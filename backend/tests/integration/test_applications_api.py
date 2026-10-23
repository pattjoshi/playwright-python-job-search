"""Application tracker through the web API."""

from job_search.repositories import JobHistoryRepository
from tests.integration.web_support import start, wait_done


def test_crud_through_the_api(make_client):
    client, _ = make_client()
    assert client.post("/api/applications", json={"title": "SDET"}).json() == {"error": "Company is required."}

    app = client.post("/api/applications", json={"company": "Infosys", "title": "SDET", "url": "https://x.test/1"}).json()["application"]
    edited = client.patch(f"/api/applications/{app['id']}", json={"status": "screening", "contact": "Priya (HR)"}).json()["application"]
    assert edited["status"] == "screening" and edited["contact"] == "Priya (HR)"

    detail = client.get(f"/api/applications/{app['id']}").json()
    assert [e["to_status"] for e in detail["events"]] == ["screening", "saved"]
    listed = client.get("/api/applications?q=info").json()
    assert [a["id"] for a in listed["applications"]] == [app["id"]] and "interview" in listed["statuses"]
    assert client.get("/api/applications/stats").json()["by_status"] == {"screening": 1}

    assert client.delete(f"/api/applications/{app['id']}").json() == {"ok": True}
    assert client.get(f"/api/applications/{app['id']}").status_code == 404


def test_track_from_search_results_and_mark_applied(make_client):
    client, _ = make_client()
    wait_done(client, start(client).json()["id"])
    job = {"source": "linkedin", "job_id": "linkedin0", "title": "Job 0", "company": "Co", "url": "https://example.com/linkedin/0"}

    tracked = client.post("/api/applications/track", json=job).json()
    assert tracked["created"] and tracked["application"]["status"] == "saved"
    marked = client.post("/api/jobs/status", json={**job, "status": "applied"}).json()
    assert marked["tracked"] is False  # already in the tracker, just moved to Applied
    assert client.get("/api/applications").json()["applications"][0]["status"] == "applied"

    other = {**job, "job_id": "linkedin1", "title": "Job 1"}
    assert client.post("/api/jobs/status", json={**other, "status": "applied"}).json()["tracked"] is True
    assert len(client.get("/api/applications").json()["applications"]) == 2


def test_import_jobs_marked_applied_before(make_client, tmp_path):
    client, _ = make_client()
    # Jobs marked applied in searches before the tracker existed.
    JobHistoryRepository(tmp_path / "history.sqlite3").set_status("naukri", "old1", "applied", title="QA", company="HCL")

    assert client.post("/api/applications/import-applied").json() == {"added": 1}
    assert client.post("/api/applications/import-applied").json() == {"added": 0}  # only once
    assert client.get("/api/applications").json()["applications"][0]["company"] == "HCL"
