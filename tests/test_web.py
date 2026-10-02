import io
import logging
import threading
import time

import pytest

from job_search.config import Settings
from job_search.models import Job, Profile
from job_search.pipeline import SearchResult
from job_search.web import create_app


class FakeRunner:
    """Stands in for pipeline.run: records options and returns canned results."""

    def __init__(self, output_dir, fail=False, block=None):
        self.output_dir = output_dir
        self.fail = fail
        self.block = block
        self.options = None

    def __call__(self, options, settings, on_profile=None):
        self.options = options
        if self.block:
            self.block.wait(5)
        logging.getLogger("job_search.pipeline").info("LinkedIn: 'SDET' in 'Pune', page 1")
        on_profile(Profile(summary="QA engineer", skills=["Python"]), ["SDET"], ["Pune"])
        if self.fail:
            raise ValueError("No text could be extracted from resume.pdf")
        html, xlsx, csv = (self.output_dir / name for name in ("r.html", "r.xlsx", "r.csv"))
        for path in (html, xlsx, csv):
            path.write_text("x")
        jobs = {
            site: [Job(site, f"{site}{i}", f"Job {i}", "Co", "Pune", f"https://example.com/{site}/{i}", score=90 - i)
                   for i in range(count)]
            for site, count in options.results_per_site.items()
        }
        all_jobs = [job for site_jobs in jobs.values() for job in site_jobs]
        return SearchResult(Profile(), all_jobs, jobs, html, xlsx, csv)


@pytest.fixture
def make_client(tmp_path):
    def make(runner=None, api_key="key", **settings):
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        runner = runner or FakeRunner(output_dir)
        app = create_app(
            Settings(openai_api_key=api_key, **settings), output_dir=output_dir, upload_dir=tmp_path / "uploads", runner=runner
        )
        return app.test_client(), runner, output_dir

    return make


def form(**overrides):
    data = {
        "resume": (io.BytesIO(b"Python QA engineer"), "My Resume.txt"),
        "site_linkedin": "on", "results_linkedin": "20",
        "site_naukri": "on", "results_naukri": "12",
        "site_indeed": "on", "results_indeed": "10",
        "hours": "24", "show_browser": "on", "keywords": "SDET, QA Automation ,", "location": "",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def wait_done(client, job_id):
    for _ in range(100):
        state = client.get(f"/api/search/{job_id}").get_json()
        if state["status"] != "running":
            return state
        time.sleep(0.02)
    raise AssertionError("search never finished")


def test_index_and_config(make_client):
    client, _, _ = make_client(results_per_site={"linkedin": 20, "naukri": 12}, location="Pune")

    assert b"Job Search" in client.get("/").data
    config = client.get("/api/config").get_json()
    assert [(s["id"], s["results"]) for s in config["sites"]] == [("linkedin", 20), ("naukri", 12), ("indeed", 10)]
    assert config["location"] == "Pune"
    assert config["has_api_key"] is True


def test_search_runs_with_per_site_counts(make_client, tmp_path):
    client, runner, _ = make_client()

    response = client.post("/api/search", data=form(), content_type="multipart/form-data")
    assert response.status_code == 202
    state = wait_done(client, response.get_json()["id"])

    assert state["status"] == "done", state
    options = runner.options
    assert options.results_per_site == {"linkedin": 20, "naukri": 12, "indeed": 10}
    assert options.sites == ["linkedin", "naukri", "indeed"]
    assert options.keywords == ["SDET", "QA Automation"]
    assert options.location is None
    assert options.headless is False
    assert options.resume_path.parent == tmp_path / "uploads"
    assert options.resume_path.name.endswith("My_Resume.txt")

    assert state["profile"]["keywords"] == ["SDET"]
    assert any("LinkedIn" in line for line in state["logs"])
    sites = {site["id"]: site for site in state["result"]["sites"]}
    assert [len(sites[s]["jobs"]) for s in ("linkedin", "naukri", "indeed")] == [20, 12, 10]
    assert sites["naukri"]["name"] == "Naukri"
    assert client.get(state["result"]["html_report"]).status_code == 200


def test_only_checked_sites_are_searched(make_client):
    client, runner, _ = make_client()
    data = form(site_naukri=None, site_indeed=None, show_browser=None)

    job_id = client.post("/api/search", data=data, content_type="multipart/form-data").get_json()["id"]
    wait_done(client, job_id)

    assert runner.options.sites == ["linkedin"]
    assert runner.options.results_per_site == {"linkedin": 20}
    assert runner.options.headless is True


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"resume": None}, "Choose your resume"),
        ({"resume": (io.BytesIO(b"x"), "resume.exe")}, "Resume must be one of"),
        ({"site_linkedin": None, "site_naukri": None, "site_indeed": None}, "at least one job site"),
        ({"results_naukri": "0"}, "between 1 and 100"),
        ({"results_naukri": "lots"}, "between 1 and 100"),
        ({"hours": "0"}, "Posted within"),
    ],
)
def test_bad_input_is_explained(make_client, overrides, message):
    client, _, _ = make_client()
    response = client.post("/api/search", data=form(**overrides), content_type="multipart/form-data")
    assert response.status_code == 400
    assert message in response.get_json()["error"]


def test_missing_api_key(make_client):
    client, _, _ = make_client(api_key=None)
    response = client.post("/api/search", data=form(), content_type="multipart/form-data")
    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.get_json()["error"]


def test_failed_search_reports_error(make_client, tmp_path):
    client, _, _ = make_client(runner=FakeRunner(tmp_path, fail=True))
    job_id = client.post("/api/search", data=form(), content_type="multipart/form-data").get_json()["id"]

    state = wait_done(client, job_id)

    assert state["status"] == "error"
    assert "No text could be extracted" in state["error"]


def test_one_search_at_a_time(make_client, tmp_path):
    release = threading.Event()
    client, _, _ = make_client(runner=FakeRunner(tmp_path, block=release))

    first = client.post("/api/search", data=form(), content_type="multipart/form-data")
    second = client.post("/api/search", data=form(), content_type="multipart/form-data")
    assert client.get("/api/config").get_json()["running_job"] == first.get_json()["id"]
    release.set()

    assert second.status_code == 409
    assert "already running" in second.get_json()["error"]
    wait_done(client, first.get_json()["id"])


def test_unknown_job_and_report_paths(make_client):
    client, _, _ = make_client()
    assert client.get("/api/search/nope").status_code == 404
    assert client.get("/reports/../../etc/passwd").status_code == 404
