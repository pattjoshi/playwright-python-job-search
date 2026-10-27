from fastapi.testclient import TestClient

from job_search.services.auth.passwords import hash_password
from job_search.services.openai_key import OpenAIKeyError

KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789"


def test_save_check_and_remove_the_key(make_client, tmp_path):
    def checker(key):
        if "refused" in key:
            raise OpenAIKeyError("OpenAI didn't accept this key.")

    client, _ = make_client(api_key=None, key_checker=checker)
    assert client.get("/api/settings/openai-key").json() == {"source": None, "hint": None}
    assert client.get("/api/config").json()["has_api_key"] is False
    assert "Settings" in client.post("/api/search", json={}).json()["error"]

    bad = client.put("/api/settings/openai-key", json={"key": "nope"})
    assert bad.status_code == 400 and "doesn't look like an OpenAI key" in bad.json()["error"]
    refused = client.put("/api/settings/openai-key", json={"key": "sk-refused-0000000000000000000000"})
    assert refused.status_code == 400 and "didn't accept" in refused.json()["error"]

    saved = client.put("/api/settings/openai-key", json={"key": KEY})
    assert saved.json() == {"source": "settings", "hint": "sk-…6789"}
    assert KEY not in saved.text and KEY not in client.get("/api/settings/openai-key").text  # never sent back
    assert client.get("/api/config").json()["has_api_key"] is True
    assert client.app.state.context.settings.api_key() == KEY  # used at once, no restart
    assert KEY not in (tmp_path / "secrets.json").read_text()

    assert client.delete("/api/settings/openai-key").json() == {"source": None, "hint": None}


def test_only_the_owner_changes_the_key(make_client):
    client, _ = make_client()
    ctx = client.app.state.context
    ctx.auth.users.create("guest@example.com", "Guest", hash_password("guest password 1"), role="member")
    guest = TestClient(client.app)
    assert guest.post("/api/auth/login", json={"email": "guest@example.com", "password": "guest password 1"}).status_code == 200
    assert guest.put("/api/settings/openai-key", json={"key": KEY}).status_code == 403
    assert guest.delete("/api/settings/openai-key").status_code == 403
    assert TestClient(client.app).get("/api/settings/openai-key").status_code == 401  # signed out
