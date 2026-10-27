"""Access control through the web API: sign-in is required, cookies are safe, roles are enforced."""

from fastapi.testclient import TestClient

from job_search.api.app import create_app
from job_search.config import Settings
from job_search.repositories import UserRepository
from job_search.services.auth.passwords import hash_password
from tests.auth_helpers import OWNER, signed_in
from tests.integration.web_support import PROFILE, FakeScheduler


def make_client(tmp_path) -> TestClient:
    app = create_app(
        Settings("key", history_path=tmp_path / "history.sqlite3"), output_dir=tmp_path / "out",
        upload_dir=tmp_path / "up", analyzer=lambda path: PROFILE, system_scheduler=FakeScheduler(),
        frontend_dir=tmp_path / "frontend",
    )
    return TestClient(app, base_url="http://127.0.0.1")


def test_everything_needs_sign_in_except_sign_in_itself(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/auth/status").json() == {"setup_required": True, "setup_code_required": False, "user": None}
    for path in ("/api/config", "/api/session", "/api/runs", "/api/schedule", "/reports/jobs.html"):
        response = client.get(path)
        assert response.status_code == 401 and response.json() == {"error": "Please sign in."}, path
    assert client.post("/api/search", json={}).status_code == 401
    assert client.get("/").status_code == 200  # the page itself is public; it shows the sign-in screen


def test_first_run_setup_then_sign_in(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/api/auth/setup", json={**OWNER, "password": "short"}).json()["error"].startswith("Use at least 8")
    assert client.post("/api/auth/setup", json={**OWNER, "email": "nope"}).json()["error"] == "Enter a valid email address."

    response = client.post("/api/auth/setup", json=OWNER)
    assert response.status_code == 200 and response.json()["user"]["role"] == "owner"
    cookie = response.headers["set-cookie"].lower()
    assert "job_search_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/config").status_code == 200
    assert client.get("/api/auth/status").json()["user"]["email"] == OWNER["email"]

    assert make_client(tmp_path).post("/api/auth/setup", json=OWNER).status_code == 409  # only once


def test_wrong_password_logout_and_throttling(tmp_path):
    signed_in(make_client(tmp_path))
    client = make_client(tmp_path)
    for _ in range(5):
        assert client.post("/api/auth/login", json={**OWNER, "password": "wrong password"}).status_code == 401
    blocked = client.post("/api/auth/login", json=OWNER)
    assert blocked.status_code == 429 and "Too many tries" in blocked.json()["error"]

    other = signed_in(make_client(tmp_path))
    assert other.post("/api/auth/logout").json() == {"ok": True}
    assert other.get("/api/config").status_code == 401


def test_requests_from_other_websites_are_refused(tmp_path):
    client = signed_in(make_client(tmp_path))
    evil = client.post("/api/history/forget", headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert client.post("/api/history/forget", headers={"Origin": "http://localhost:3000"}).status_code == 200
    assert client.post("/api/history/forget", headers={"Origin": "http://127.0.0.1"}).status_code == 200
    # Another web page on this computer (other port) is another origin, though the browser sends it the cookie.
    assert client.post("/api/history/forget", headers={"Origin": "http://127.0.0.1:5000"}).status_code == 403
    assert client.post("/api/history/forget", headers={"Origin": "http://localhost:8888"}).status_code == 403


def test_only_the_owner_can_change_the_daily_search(tmp_path):
    signed_in(make_client(tmp_path))
    UserRepository(tmp_path / "history.sqlite3").create("member@example.com", "M", hash_password("member password"), "member")
    member = make_client(tmp_path)
    member.post("/api/auth/login", json={"email": "member@example.com", "password": "member password"})
    assert member.get("/api/schedule").status_code == 200
    response = member.delete("/api/schedule")
    assert response.status_code == 403 and response.json()["error"] == "Only the owner of this app can do that."


def test_change_password_and_sign_out_everywhere(tmp_path):
    client = signed_in(make_client(tmp_path))
    other = signed_in(make_client(tmp_path))
    assert client.post("/api/auth/password", json={"current": "nope", "new": "another long one"}).status_code == 403
    assert client.post("/api/auth/password", json={"current": OWNER["password"], "new": "another long one"}).status_code == 200
    assert client.get("/api/config").status_code == 200 and other.get("/api/config").status_code == 401

    assert client.post("/api/auth/logout-everywhere").status_code == 200
    assert client.get("/api/config").status_code == 401
