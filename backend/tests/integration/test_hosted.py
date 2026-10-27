"""Online (Vercel) mode: the first account needs SETUP_CODE, local-only actions are refused, cookies are Secure."""

from fastapi.testclient import TestClient

from job_search.api.app import create_app
from job_search.config import Settings, load_settings
from tests.auth_helpers import OWNER
from tests.integration.web_support import PROFILE, FakeScheduler


def hosted_client(tmp_path, setup_code="let-me-in"):
    app = create_app(
        Settings("key", history_path=tmp_path / "history.sqlite3", hosted=True, setup_code=setup_code), output_dir=tmp_path / "out",
        upload_dir=tmp_path / "up", analyzer=lambda path: PROFILE, system_scheduler=FakeScheduler(),
        frontend_dir=tmp_path / "frontend", key_checker=lambda key: None,
    )
    return TestClient(app, base_url="https://127.0.0.1")


def test_first_account_needs_the_setup_code(tmp_path):
    client = hosted_client(tmp_path)
    assert client.get("/api/auth/status").json()["setup_code_required"] is True
    assert client.post("/api/auth/setup", json=OWNER).status_code == 403
    assert client.post("/api/auth/setup", json={**OWNER, "setup_code": "guess"}).status_code == 403
    created = client.post("/api/auth/setup", json={**OWNER, "setup_code": "let-me-in"})
    assert created.status_code == 200
    cookie = created.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie  # only sent over HTTPS, never readable by page scripts
    assert client.get("/api/config").json()["hosted"] is True


def test_no_setup_code_means_no_sign_up_online(tmp_path):
    response = hosted_client(tmp_path, setup_code=None).post("/api/auth/setup", json={**OWNER, "setup_code": ""})
    assert response.status_code == 403 and "SETUP_CODE" in response.json()["error"]


def test_local_only_actions_are_refused_online(tmp_path):
    client = hosted_client(tmp_path)
    client.post("/api/auth/setup", json={**OWNER, "setup_code": "let-me-in"})
    for method, path in (("post", "/api/search"), ("post", "/api/analyze"), ("post", "/api/schedule"),
                         ("put", "/api/settings/openai-key")):
        response = getattr(client, method)(path, json={})
        assert response.status_code == 409 and "on your computer only" in response.json()["error"], path
    # What works online keeps working.
    created = client.post("/api/applications", json={"title": "QA", "company": "Acme", "status": "applied"})
    assert created.status_code == 200, created.text
    assert client.post("/api/notes", json={"title": "Interview prep"}).status_code == 200


def test_wrong_passwords_are_counted_per_real_visitor(tmp_path):
    client = hosted_client(tmp_path)
    client.post("/api/auth/setup", json={**OWNER, "setup_code": "let-me-in"})
    login = {"email": OWNER["email"], "password": "wrong password!"}
    for _ in range(5):
        client.post("/api/auth/login", json=login, headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"})
    assert client.post("/api/auth/login", json=login, headers={"X-Forwarded-For": "203.0.113.7"}).status_code == 429
    # Another visitor (another address behind the same proxy) isn't locked out by them.
    other = client.post("/api/auth/login", json={**login, "password": OWNER["password"]}, headers={"X-Forwarded-For": "198.51.100.2"})
    assert other.status_code == 200


def test_vercel_addresses_are_allowed(monkeypatch):
    monkeypatch.setenv("VERCEL_URL", "job-search-abc123.vercel.app")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "job-search.vercel.app")
    monkeypatch.setenv("ALLOWED_HOSTS", "jobs.example.com")
    hosts = load_settings().allowed_hosts
    assert {"job-search-abc123.vercel.app", "job-search.vercel.app", "jobs.example.com"} <= set(hosts)
