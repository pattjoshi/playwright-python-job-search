"""Web API: resume upload, config and running a search."""

import threading

import pytest

from tests.integration.web_support import PROFILE, FakeRunner, search_body, start, upload, wait_done


def test_frontend_page_or_build_hint(make_client, tmp_path):
    client, _ = make_client()
    assert b"npm run build" in client.get("/").content  # not built yet: explains how

    built = tmp_path / "frontend"
    (built / "_next").mkdir(parents=True)
    (built / "index.html").write_text("<title>Job Search</title>")
    (built / "_next" / "app.js").write_text("console.log(1)")
    client, _ = make_client()
    assert b"<title>Job Search</title>" in client.get("/").content
    assert client.get("/_next/app.js").text == "console.log(1)"
    assert client.get("/api/session").json() == {"resume": None, "last_job": None}  # API still wins


def test_config(make_client):
    client, _ = make_client(results_per_site={"linkedin": 20, "naukri": 12}, locations=["Pune"], experience=(1, 2))

    config = client.get("/api/config").json()
    assert [(s["id"], s["results"]) for s in config["sites"]] == [("linkedin", 20), ("naukri", 12), ("indeed", 10)]
    assert config["defaults"]["locations"] == ["Pune"]
    assert config["defaults"]["experience"] == [1, 2]
    assert config["location_choices"][:3] == ["Remote", "Bengaluru", "Hyderabad"]
    assert config["history"] == {"seen": 0, "applied": 0, "hidden": 0}


def test_analyze_resume_suggests_settings(make_client, tmp_path):
    client, _ = make_client()

    body = upload(client).json()

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
    assert "Choose your resume" in client.post("/api/analyze").json()["error"]
    assert "Resume must be one of" in upload(client, name="cv.exe").json()["error"]
    response = upload(client)
    assert response.status_code == 400
    assert "No text could be extracted" in response.json()["error"]


def test_search_runs_with_all_settings(make_client):
    client, runner = make_client()

    response = start(client)
    assert response.status_code == 202, response.json()
    state = wait_done(client, response.json()["id"])

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
    job_id = start(client, experience=None, locations=[], keywords=[]).json()["id"]
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
    resume_id = upload(client).json()["resume_id"]
    body = search_body(resume_id)
    body.update(overrides)

    response = client.post("/api/search", json=body)

    assert response.status_code == 400
    assert message in response.json()["error"]


def test_missing_api_key(make_client):
    client, _ = make_client(api_key=None)
    response = client.post("/api/search", json=search_body("x"))
    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.json()["error"]


def test_failed_search_reports_error(make_client, tmp_path):
    client, _ = make_client(runner=FakeRunner(tmp_path, fail=True))
    state = wait_done(client, start(client).json()["id"])
    assert state["status"] == "error"
    assert "No text could be extracted" in state["error"]


def test_stop_search(make_client, tmp_path):
    client, _ = make_client(runner=FakeRunner(tmp_path, block=threading.Event()))
    job_id = start(client).json()["id"]

    stopping = client.post(f"/api/search/{job_id}/stop").json()
    state = wait_done(client, job_id)

    assert stopping["status"] == "stopping"
    assert state["status"] == "stopped"
    assert state["result"] is None
    assert client.get("/api/config").json()["running_job"] is None


def test_one_search_at_a_time(make_client, tmp_path):
    release = threading.Event()
    client, _ = make_client(runner=FakeRunner(tmp_path, block=release))

    first = start(client)
    second = start(client)
    assert client.get("/api/config").json()["running_job"] == first.json()["id"]
    release.set()

    assert second.status_code == 409
    assert "already running" in second.json()["error"]
    wait_done(client, first.json()["id"])
