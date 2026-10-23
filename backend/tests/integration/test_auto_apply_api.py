"""Auto-apply through the web API (no job pages are opened)."""

import time

from tests.integration.web_support import start, wait_done


def test_settings_queue_and_run(make_client):
    client, _ = make_client()
    overview = client.get("/api/auto-apply").json()
    assert overview["settings"]["dry_run"] is True and overview["jobs"] == [] and overview["run"]["status"] == "idle"
    assert client.put("/api/auto-apply/settings", json={"daily_limit": 500}).status_code == 400
    saved = client.put("/api/auto-apply/settings", json={"min_score": 0, "dry_run": False}).json()["settings"]
    assert saved["min_score"] == 0 and saved["dry_run"] is False

    wait_done(client, start(client).json()["id"])  # the fake search's jobs have no company links...
    assert client.post("/api/auto-apply/queue-last-search").json() == {"added": 0}

    assert client.post("/api/auto-apply/run").json()["run"]["status"] == "running"
    for _ in range(50):
        run = client.get("/api/auto-apply").json()["run"]
        if run["status"] not in ("running", "stopping"):
            break
        time.sleep(0.05)
    assert run["status"] == "done"  # nothing queued: done straight away

    assert client.post("/api/auto-apply/999/retry").status_code == 404
    assert client.delete("/api/auto-apply/999").status_code == 404
    assert client.get("/api/auto-apply/999/screenshot").status_code == 404
    client.post("/api/auth/logout")
    assert client.get("/api/auto-apply").status_code == 401
