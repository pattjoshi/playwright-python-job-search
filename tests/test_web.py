import io
import logging
import threading
import time

import pytest

from job_search.config import Settings
from job_search.models import Job, Profile
from job_search.pipeline import SearchResult
from job_search.utils import SearchStopped
from job_search.web import create_app, suggest_experience

PROFILE = Profile(
    current_title="QA Engineer",
    skills=["Python"],
    years_experience=4,
    locations=["Bangalore, Karnataka", "Pune"],
    search_queries=["SDET", "QA Automation"],
    summary="QA engineer",
)


class FakeRunner:
    """Stands in for pipeline.run: records options, reports progress, returns canned results."""

    def __init__(self, output_dir, fail=False, block=None):
        self.output_dir = output_dir
        self.fail = fail
        self.block = block
        self.options = None

    def __call__(self, options, settings, on_event=None, stop_event=None):
        self.options = options
        on_event("stage", {"stage": "search"})
        on_event("funnel", {"steps": [("found", 169), ("unique", 120), ("scored", 3)]})
        on_event("site", {"site": "linkedin", "status": "running", "found": 0})
        if self.block:
            # Wait until the test releases us or presses Stop.
            while not self.block.is_set():
                if stop_event.is_set():
                    raise SearchStopped()
                time.sleep(0.01)
        logging.getLogger("job_search.pipeline").info("LinkedIn: 'SDET' in 'Pune', page 1")
        on_event("profile", {"profile": options.profile, "queries": ["SDET"], "locations": ["Pune"]})
        if self.fail:
            raise ValueError("No text could be extracted from resume.pdf")
        html, xlsx, csv = (self.output_dir / name for name in ("r.html", "r.xlsx", "r.csv"))
        for path in (html, xlsx, csv):
            path.write_text("x")
        jobs = {
            site: [
                Job(site, f"{site}{i}", f"Job {i}", "Co", "Pune", f"https://example.com/{site}/{i}", score=90 - i, experience="1-3 Yrs")
                for i in range(count)
            ]
            for site, count in options.results_per_site.items()
        }
        all_jobs = [job for site_jobs in jobs.values() for job in site_jobs]
        return SearchResult(Profile(), all_jobs, jobs, html, xlsx, csv)


@pytest.fixture
def make_client(tmp_path):
    def make(runner=None, api_key="key", analyzer=None, **settings):
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        runner = runner or FakeRunner(output_dir)
        app = create_app(
            Settings(openai_api_key=api_key, history_path=tmp_path / "history.sqlite3", **settings),
            output_dir=output_dir,
            upload_dir=tmp_path / "uploads",
            runner=runner,
            analyzer=analyzer or (lambda path: PROFILE),
        )
        return app.test_client(), runner

    return make


def upload(client, name="My Resume.txt", content=b"Python QA engineer"):
    return client.post("/api/analyze", data={"resume": (io.BytesIO(content), name)}, content_type="multipart/form-data")


def search_body(resume_id, **overrides):
    body = {
        "resume_id": resume_id,
        "sites": {"linkedin": 20, "naukri": 12, "indeed": 10},
        "keywords": ["SDET", " QA  Automation ", "SDET"],
        "locations": ["Pune", "Remote"],
        "experience": [1, 2],
        "hours": 24,
        "only_new": True,
        "show_browser": True,
        "max_pages": 2,
        "top": 30,
    }
    body.update(overrides)
    return body


def start(client, **overrides):
    resume_id = upload(client).get_json()["resume_id"]
    return client.post("/api/search", json=search_body(resume_id, **overrides))


def wait_done(client, job_id):
    for _ in range(300):
        state = client.get(f"/api/search/{job_id}").get_json()
        if state["status"] not in ("running", "stopping"):
            return state
        time.sleep(0.01)
    raise AssertionError("search never finished")


def test_index_and_config(make_client):
    client, _ = make_client(results_per_site={"linkedin": 20, "naukri": 12}, locations=["Pune"], experience=(1, 2))

    assert b"Job Search" in client.get("/").data
    config = client.get("/api/config").get_json()
    assert [(s["id"], s["results"]) for s in config["sites"]] == [("linkedin", 20), ("naukri", 12), ("indeed", 10)]
    assert config["defaults"]["locations"] == ["Pune"]
    assert config["defaults"]["experience"] == [1, 2]
    assert config["location_choices"][:3] == ["Remote", "Bengaluru", "Hyderabad"]
    assert config["history"] == {"seen": 0, "applied": 0, "hidden": 0}


def test_analyze_resume_suggests_settings(make_client, tmp_path):
    client, _ = make_client()

    body = upload(client).get_json()

    assert body["file_name"] == "My Resume.txt"
    assert body["profile"]["keywords"] == ["SDET", "QA Automation"]
    assert body["profile"]["locations"] == ["Bengaluru", "Pune"]
    assert body["suggested_experience"] == [3, 5]
    saved = list((tmp_path / "uploads").iterdir())
    assert len(saved) == 1 and saved[0].name.endswith("My_Resume.txt")


def test_analyze_errors(make_client):
    def broken(path):
        raise ValueError("No text could be extracted")

    client, _ = make_client(analyzer=broken)
    assert "Choose your resume" in client.post("/api/analyze", data={}).get_json()["error"]
    assert "Resume must be one of" in upload(client, name="cv.exe").get_json()["error"]
    response = upload(client)
    assert response.status_code == 400
    assert "No text could be extracted" in response.get_json()["error"]


def test_search_runs_with_all_settings(make_client):
    client, runner = make_client()

    response = start(client)
    assert response.status_code == 202, response.get_json()
    state = wait_done(client, response.get_json()["id"])

    assert state["status"] == "done", state
    options = runner.options
    assert options.results_per_site == {"linkedin": 20, "naukri": 12, "indeed": 10}
    assert options.sites == ["linkedin", "naukri", "indeed"]
    assert options.keywords == ["SDET", "QA Automation"]
    assert options.locations == ["Pune", "Remote"]
    assert options.experience == (1, 2)
    assert (options.max_age_hours, options.max_pages, options.top_n) == (24, 2, 30)
    assert options.only_new is True
    assert options.headless is False
    assert options.profile is PROFILE  # resume isn't sent to the AI twice

    assert state["stage"] == "search"
    assert state["sites"]["linkedin"] == {"status": "running", "found": 0}
    assert state["sites"]["naukri"] == {"status": "waiting", "found": 0}
    assert state["funnel"] == [["found", 169], ["unique", 120], ["scored", 3]]
    assert state["profile"]["keywords"] == ["SDET"]
    assert any("LinkedIn" in line for line in state["logs"])
    sites = {site["id"]: site for site in state["result"]["sites"]}
    assert [len(sites[s]["jobs"]) for s in ("linkedin", "naukri", "indeed")] == [20, 12, 10]
    job = sites["naukri"]["jobs"][0]
    assert (job["job_id"], job["experience"], job["is_new"]) == ("naukri0", "1-3 Yrs", True)
    assert client.get(state["result"]["html_report"]).status_code == 200


def test_any_experience_and_auto_locations(make_client):
    client, runner = make_client()
    job_id = start(client, experience=None, locations=[], keywords=[]).get_json()["id"]
    wait_done(client, job_id)
    assert (runner.options.experience, runner.options.locations, runner.options.keywords) == (None, [], [])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"resume_id": "missing"}, "Upload your resume"),
        ({"sites": {}}, "at least one job site"),
        ({"sites": {"monster": 5}}, "Unknown job site"),
        ({"sites": {"naukri": 0}}, "between 1 and 100"),
        ({"sites": {"naukri": "lots"}}, "whole number"),
        ({"experience": [5, 2]}, "can't be more than"),
        ({"experience": [1]}, "'from' and a 'to'"),
        ({"experience": [1, 99]}, "between 0 and 50"),
        ({"hours": 0}, "Posted within"),
        ({"locations": "Pune"}, "must be a list"),
        ({"locations": [f"City {i}" for i in range(11)]}, "at most 10 locations"),
    ],
)
def test_bad_search_settings_are_explained(make_client, overrides, message):
    client, _ = make_client()
    resume_id = upload(client).get_json()["resume_id"]
    body = search_body(resume_id)
    body.update(overrides)

    response = client.post("/api/search", json=body)

    assert response.status_code == 400
    assert message in response.get_json()["error"]


def test_missing_api_key(make_client):
    client, _ = make_client(api_key=None)
    response = client.post("/api/search", json=search_body("x"))
    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.get_json()["error"]


def test_failed_search_reports_error(make_client, tmp_path):
    client, _ = make_client(runner=FakeRunner(tmp_path, fail=True))
    state = wait_done(client, start(client).get_json()["id"])
    assert state["status"] == "error"
    assert "No text could be extracted" in state["error"]


def test_stop_search(make_client, tmp_path):
    client, _ = make_client(runner=FakeRunner(tmp_path, block=threading.Event()))
    job_id = start(client).get_json()["id"]

    stopping = client.post(f"/api/search/{job_id}/stop").get_json()
    state = wait_done(client, job_id)

    assert stopping["status"] == "stopping"
    assert state["status"] == "stopped"
    assert state["result"] is None
    assert client.get("/api/config").get_json()["running_job"] is None


def test_one_search_at_a_time(make_client, tmp_path):
    release = threading.Event()
    client, _ = make_client(runner=FakeRunner(tmp_path, block=release))

    first = start(client)
    second = start(client)
    assert client.get("/api/config").get_json()["running_job"] == first.get_json()["id"]
    release.set()

    assert second.status_code == 409
    assert "already running" in second.get_json()["error"]
    wait_done(client, first.get_json()["id"])


def test_mark_applied_hidden_and_forget(make_client):
    client, _ = make_client()

    for job_id, status in (("1", "applied"), ("2", "hidden"), ("3", "seen")):
        response = client.post("/api/jobs/status", json={"source": "linkedin", "job_id": job_id, "status": status, "title": "QA"})
        assert response.status_code == 200
    assert response.get_json()["history"] == {"seen": 1, "applied": 1, "hidden": 1}

    bad = client.post("/api/jobs/status", json={"source": "linkedin", "job_id": "1", "status": "loved"})
    assert bad.status_code == 400

    forgot = client.post("/api/history/forget").get_json()
    assert forgot == {"forgotten": 1, "history": {"seen": 0, "applied": 1, "hidden": 1}}


def test_unknown_job_and_report_paths(make_client):
    client, _ = make_client()
    assert client.get("/api/search/nope").status_code == 404
    assert client.post("/api/search/nope/stop").status_code == 404
    assert client.get("/reports/../../etc/passwd").status_code == 404


@pytest.mark.parametrize(("years", "expected"), [(4, [3, 5]), (0.5, [0, 2]), (0, [0, 1]), (None, None)])
def test_suggest_experience(years, expected):
    assert suggest_experience(years) == expected


def test_list_history(make_client):
    client, _ = make_client()
    client.post("/api/jobs/status", json={"source": "naukri", "job_id": "9", "status": "applied", "title": "SDET", "url": "https://x.y/9"})

    body = client.get("/api/history?status=applied").get_json()

    assert [job["title"] for job in body["jobs"]] == ["SDET"]
    assert body["history"]["applied"] == 1
    assert client.get("/api/history?status=hidden").get_json()["jobs"] == []
    assert client.get("/api/history?status=loved").status_code == 400
