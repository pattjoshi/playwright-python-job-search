"""The Chrome extension's API: connecting with a key, claiming jobs, answers, results (no browser)."""

import base64

from fastapi.testclient import TestClient

from job_search.models import Job

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()


def connect(client):
    key = client.post("/api/auto-apply/extension-key").json()["key"]
    extension = TestClient(client.app, base_url="http://127.0.0.1", headers={"Authorization": f"Bearer {key}", "Origin": "chrome-extension://abcdef"})
    return key, extension


def test_key_connects_and_replacing_it_disconnects(make_client):
    client, _ = make_client()
    assert client.get("/api/auto-apply").json()["extension"]["connected"] is False
    key, extension = connect(client)
    assert key.startswith("jsa_")
    status = extension.get("/api/extension/status").json()
    assert status["dry_run"] is True and status["waiting"] == 0 and set(status["boards"]) == {"naukri", "linkedin", "indeed"}
    assert client.get("/api/auto-apply").json()["extension"]["connected"] is True

    assert TestClient(client.app, base_url="http://127.0.0.1").get("/api/extension/status").status_code == 401  # no key
    wrong = TestClient(client.app, base_url="http://127.0.0.1", headers={"Authorization": "Bearer jsa_wrong"})
    assert wrong.get("/api/extension/status").status_code == 401
    _, newer = connect(client)
    assert extension.get("/api/extension/status").status_code == 401  # the old key stopped working
    assert newer.get("/api/extension/status").status_code == 200
    client.delete("/api/auto-apply/extension-key")
    assert newer.get("/api/extension/status").status_code == 401


def test_claim_answer_report(make_client):
    client, _ = make_client()
    _, extension = connect(client)
    client.put("/api/auto-apply/settings", json={"linkedin": True, "min_score": 0})
    jobs = [Job("linkedin", "4012345678", "QA", "Acme", "Pune", "https://in.linkedin.com/jobs/view/qa-at-acme-4012345678", score=90),
            Job("naukri", "2", "SDET", "Beta", "Pune", "https://www.naukri.com/job-2", score=95)]  # Naukri is off
    client.app.state.context.auto_apply.service.queue_jobs(1, jobs)

    claimed = extension.post("/api/extension/next").json()["job"]
    assert claimed["platform"] == "linkedin" and claimed["url"] == "https://www.linkedin.com/jobs/view/4012345678/"
    assert claimed["dry_run"] is True
    assert extension.post("/api/extension/next").json()["job"] is None  # nothing else on a board that's on

    client.post("/api/answers", json={"question": "Mobile phone number", "answer": "9876543210"})
    known = extension.post(f"/api/extension/jobs/{claimed['id']}/answer", json={"question": "Mobile phone number"}).json()
    assert known == {"answer": "9876543210", "how": "saved"}
    unknown = extension.post(f"/api/extension/jobs/{claimed['id']}/answer", json={"question": "Notice period in days?", "options": []})
    assert unknown.json()["answer"] is None
    assert client.get("/api/answers?status=needs_answer").json()["answers"][0]["asked_by"] == "Acme · QA"

    bad = extension.post(f"/api/extension/jobs/{claimed['id']}/result", json={"status": "great"})
    assert bad.status_code == 400
    done = extension.post(f"/api/extension/jobs/{claimed['id']}/result", json={
        "status": "submitted", "message": "Submitted.",
        "answers": [{"question": "Mobile phone number", "answer": "9876543210", "how": "saved"}],
        "screenshot": PNG, "signed_in": True,
    }).json()["job"]
    assert done["status"] == "submitted" and done["screenshot"] == f"{claimed['id']}.png"
    assert client.get(f"/api/auto-apply/{claimed['id']}/screenshot").status_code == 200
    assert client.get("/api/applications").json()["applications"][0]["status"] == "applied"
    assert client.get("/api/auto-apply").json()["boards"]["linkedin"]["signed_in"] is True
    assert extension.post("/api/extension/jobs/999/answer", json={"question": "x"}).status_code == 404
    assert extension.get("/api/extension/resume").status_code == 404  # no resume uploaded yet
