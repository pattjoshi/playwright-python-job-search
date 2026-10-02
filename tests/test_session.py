"""The web page's session survives reloads and app restarts until "Clear"."""

import io
import os
import threading
import time
from pathlib import Path

import pytest

from job_search.cleanup import cleanup
from job_search.config import Settings
from job_search.models import Job, Profile
from job_search.pipeline import SearchResult
from job_search.session import SessionStore
from job_search.utils import SearchStopped
from job_search.web import create_app

PROFILE = Profile(current_title="GenAI Engineer", skills=["Python"], years_experience=3,
                  locations=["Bangalore"], search_queries=["GenAI Engineer"], summary="GenAI engineer")


class FakeScheduler:
    kind = "windows"


class FakeRunner:
    def __init__(self, output_dir, block=None):
        self.output_dir, self.block, self.calls = output_dir, block, 0

    def __call__(self, options, settings, on_event=None, stop_event=None):
        self.calls += 1
        while self.block and not self.block.is_set():
            if stop_event.is_set():
                raise SearchStopped()
            time.sleep(0.01)
        on_event("stage", {"stage": "report"})
        on_event("funnel", {"steps": [("found", 10), ("scored", 2)]})
        html = self.output_dir / "jobs_1.html"
        for path in (html, html.with_suffix(".xlsx"), html.with_suffix(".csv")):
            path.write_text("x")
        jobs = {"naukri": [Job("naukri", "n1", "SDET", "Infosys", "Pune", "https://example.com/n1", score=80),
                           Job("naukri", "n2", "QA", "TCS", "Pune", "https://example.com/n2", score=70)]}
        return SearchResult(Profile(), jobs["naukri"], jobs, html, html.with_suffix(".xlsx"), html.with_suffix(".csv"))


@pytest.fixture
def make_app(tmp_path):
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    analyzer_calls = []

    def analyzer(path):
        analyzer_calls.append(path)
        return PROFILE

    def make(runner=None):
        runner = runner or FakeRunner(output)
        app = create_app(Settings("key", history_path=tmp_path / "data" / "history.sqlite3"), output_dir=output,
                         upload_dir=tmp_path / "uploads", runner=runner, analyzer=analyzer, system_scheduler=FakeScheduler())
        return app.test_client(), runner

    make.analyzer_calls = analyzer_calls
    return make


def upload(client):
    return client.post("/api/analyze", data={"resume": (io.BytesIO(b"GenAI resume"), "Om_Resume.pdf")},
                       content_type="multipart/form-data").get_json()


def search(client, resume_id):
    return client.post("/api/search", json={"resume_id": resume_id, "sites": {"naukri": 12}, "hours": 24})


def wait_done(client, job_id):
    for _ in range(300):
        state = client.get(f"/api/search/{job_id}").get_json()
        if state["status"] not in ("running", "stopping"):
            return state
        time.sleep(0.01)
    raise AssertionError("search never finished")


def test_session_store(tmp_path):
    store = SessionStore(tmp_path)
    assert store.load() == {} and store.resume() is None

    resume = tmp_path / "cv.pdf"
    resume.write_text("x")
    store.save_resume("r1", resume, "cv.pdf", PROFILE, [2, 4])
    store.save_last_job({"id": "j1", "status": "done"})
    assert store.resume()["profile"] == PROFILE
    assert store.load()["last_job"]["id"] == "j1"

    resume.unlink()  # deleted resume file: not offered any more
    assert store.resume() is None

    store.clear()
    assert store.load() == {}
    store.path.write_text("{ not json")
    assert store.load() == {}


def test_page_reload_gets_resume_and_last_search(make_app):
    client, _ = make_app()
    assert client.get("/api/session").get_json() == {"resume": None, "last_job": None}

    resume = upload(client)
    state = wait_done(client, search(client, resume["resume_id"]).get_json()["id"])
    saved = client.get("/api/session").get_json()

    assert saved["resume"]["file_name"] == "Om_Resume.pdf"
    assert saved["resume"]["profile"]["keywords"] == ["GenAI Engineer"]
    assert saved["resume"]["profile"]["locations"] == ["Bengaluru"]
    assert saved["resume"]["suggested_experience"] == [2, 4]
    job = saved["last_job"]
    assert job["id"] == state["id"] and job["status"] == "done" and job["finished_at"]
    assert job["funnel"] == [["found", 10], ["scored", 2]]
    assert [j["title"] for j in job["result"]["sites"][0]["jobs"]] == ["SDET", "QA"]


def test_applied_and_hidden_show_after_reload(make_app):
    client, _ = make_app()
    resume = upload(client)
    wait_done(client, search(client, resume["resume_id"]).get_json()["id"])
    client.post("/api/jobs/status", json={"source": "naukri", "job_id": "n1", "status": "applied"})

    jobs = client.get("/api/session").get_json()["last_job"]["result"]["sites"][0]["jobs"]

    # n2 was never acted on (this fake search doesn't record "seen" like the real one does).
    assert [(j["job_id"], j["status"]) for j in jobs] == [("n1", "applied"), ("n2", None)]


def test_session_survives_app_restart(make_app):
    client, _ = make_app()
    resume = upload(client)
    wait_done(client, search(client, resume["resume_id"]).get_json()["id"])

    restarted, runner = make_app()  # same data folder, fresh app (like closing and reopening it)
    saved = restarted.get("/api/session").get_json()

    assert saved["resume"]["resume_id"] == resume["resume_id"]
    assert saved["last_job"]["status"] == "done"
    # The restored resume can be searched with straight away: no upload, no AI call.
    response = search(restarted, resume["resume_id"])
    assert response.status_code == 202
    wait_done(restarted, response.get_json()["id"])
    assert len(make_app.analyzer_calls) == 1


def test_clear(make_app):
    client, _ = make_app()
    resume = upload(client)
    wait_done(client, search(client, resume["resume_id"]).get_json()["id"])
    client.post("/api/jobs/status", json={"source": "naukri", "job_id": "n1", "status": "applied"})

    assert client.post("/api/session/clear").get_json() == {"resume": None, "last_job": None}
    assert client.get("/api/session").get_json() == {"resume": None, "last_job": None}
    assert "Upload your resume" in search(client, resume["resume_id"]).get_json()["error"]
    # History is kept.
    assert client.get("/api/config").get_json()["history"]["applied"] == 1

    restarted, _ = make_app()
    assert restarted.get("/api/session").get_json() == {"resume": None, "last_job": None}


def test_cannot_clear_while_searching(make_app, tmp_path):
    release = threading.Event()
    client, _ = make_app(FakeRunner(tmp_path / "output", block=release))
    resume = upload(client)
    job_id = search(client, resume["resume_id"]).get_json()["id"]

    response = client.post("/api/session/clear")
    release.set()

    assert response.status_code == 409
    wait_done(client, job_id)


def test_cleanup_keeps_what_the_page_shows(make_app, tmp_path):
    client, _ = make_app()
    resume = upload(client)
    wait_done(client, search(client, resume["resume_id"]).get_json()["id"])
    old = time.time() - 90 * 86_400
    shown = [*(tmp_path / "uploads").iterdir(), *(tmp_path / "output").iterdir()]
    for path in shown:
        os.utime(path, (old, old))
    stale = tmp_path / "output" / "jobs_old.html"
    stale.write_text("x")
    os.utime(stale, (old, old))

    cleanup(30, tmp_path / "data", tmp_path / "uploads", tmp_path / "output")

    assert all(path.exists() for path in shown)
    assert not stale.exists()
