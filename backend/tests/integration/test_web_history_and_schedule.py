"""Web API: applied/hidden jobs, history, reports and the daily search."""


import pytest

from tests.integration.web_support import FakeScheduler, search_body, upload


def test_mark_applied_hidden_and_forget(make_client):
    client, _ = make_client()

    for job_id, status in (("1", "applied"), ("2", "hidden"), ("3", "seen")):
        response = client.post("/api/jobs/status", json={"source": "linkedin", "job_id": job_id, "status": status, "title": "QA"})
        assert response.status_code == 200
    assert response.json()["history"] == {"seen": 1, "applied": 1, "hidden": 1}

    bad = client.post("/api/jobs/status", json={"source": "linkedin", "job_id": "1", "status": "loved"})
    assert bad.status_code == 400

    forgot = client.post("/api/history/forget").json()
    assert forgot == {"forgotten": 1, "history": {"seen": 0, "applied": 1, "hidden": 1}}


def test_unknown_job_and_report_paths(make_client):
    client, _ = make_client()
    assert client.get("/api/search/nope").status_code == 404
    assert client.post("/api/search/nope/stop").status_code == 404
    assert client.get("/reports/../../etc/passwd").status_code == 404


def test_list_history(make_client):
    client, _ = make_client()
    client.post("/api/jobs/status", json={"source": "naukri", "job_id": "9", "status": "applied", "title": "SDET", "url": "https://x.y/9"})

    body = client.get("/api/history?status=applied").json()

    assert [job["title"] for job in body["jobs"]] == ["SDET"]
    assert body["history"]["applied"] == 1
    assert client.get("/api/history?status=hidden").json()["jobs"] == []
    assert client.get("/api/history?status=loved").status_code == 400


def test_daily_schedule_save_status_and_turn_off(make_client):
    scheduler = FakeScheduler()
    client, _ = make_client(scheduler=scheduler)
    assert client.get("/api/schedule").json() == {"supported": True, "kind": "windows", "schedule": None, "last_run": None}

    resume_id = upload(client).json()["resume_id"]
    body = search_body(resume_id, time="09:30", days=["mon", "tue", "wed", "thu", "fri"], open_report=False)
    status = client.post("/api/schedule", json=body).json()

    schedule = status["schedule"]
    assert (schedule["time"], schedule["days"], schedule["open_report"]) == ("09:30", ["mon", "tue", "wed", "thu", "fri"], False)
    assert schedule["sites"] == {"linkedin": 20, "naukri": 12, "indeed": 10}
    assert schedule["locations"] == ["Pune", "Remote"] and schedule["experience"] == [1, 2]
    assert schedule["resume"].endswith("My_Resume.txt")
    assert schedule["next_run"].endswith("09:30")
    assert scheduler.installed.search["profile"]["skills"] == ["Python"]
    assert client.get("/api/schedule").json()["schedule"]["time"] == "09:30"

    off = client.delete("/api/schedule").json()
    assert off["schedule"] is None and scheduler.installed is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"time": "9am"}, "Time must look like"),
        ({"days": []}, "at least one day"),
        ({"sites": {}}, "at least one job site"),
        ({"resume_id": "gone"}, "Upload your resume"),
    ],
)
def test_daily_schedule_validation(make_client, overrides, message):
    client, _ = make_client()
    resume_id = upload(client).json()["resume_id"]
    body = search_body(resume_id, time="09:00", days=["mon"])
    body.update(overrides)
    response = client.post("/api/schedule", json=body)
    assert response.status_code == 400
    assert message in response.json()["error"]


def test_daily_schedule_os_error(make_client):
    client, _ = make_client(scheduler=FakeScheduler(fail=True))
    resume_id = upload(client).json()["resume_id"]
    response = client.post("/api/schedule", json=search_body(resume_id, time="09:00", days=["mon"]))
    assert response.status_code == 500
    assert "Access is denied" in response.json()["error"]
    assert client.get("/api/schedule").json()["schedule"] is None


def test_last_run_shown_with_report_link(make_client, tmp_path):
    from job_search.repositories import save_state

    client, _ = make_client()
    report = tmp_path / "output" / "jobs_x.html"
    report.write_text("x")
    save_state(tmp_path, last_run="2026-10-03T09:00:00", status="done", jobs=18, new=5, report=str(report))

    last = client.get("/api/schedule").json()["last_run"]
    assert (last["jobs"], last["new"], last["report_url"]) == (18, 5, "/reports/jobs_x.html")
