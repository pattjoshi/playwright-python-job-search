"""Protections every request gets: host check (DNS rebinding), body size limit, browser security headers."""

from fastapi.testclient import TestClient

from job_search.api.app import create_app
from job_search.api.security import MAX_BODY_BYTES, host_name
from job_search.config import Settings
from tests.auth_helpers import OWNER
from tests.integration.web_support import PROFILE, FakeScheduler


def make_app(tmp_path, **settings):
    return create_app(
        Settings("key", history_path=tmp_path / "history.sqlite3", **settings), output_dir=tmp_path / "out",
        upload_dir=tmp_path / "up", analyzer=lambda path: PROFILE, system_scheduler=FakeScheduler(),
        frontend_dir=tmp_path / "frontend",
    )


def test_only_local_addresses_are_answered(tmp_path):
    app = make_app(tmp_path)
    # A website that points its own name at this computer (DNS rebinding) can't claim the first account.
    rebound = TestClient(app, base_url="http://evil.example:8000")
    assert rebound.post("/api/auth/setup", json=OWNER).status_code == 400
    assert rebound.get("/api/auth/status").status_code == 400
    for base in ("http://127.0.0.1:8000", "http://localhost:8000"):
        assert TestClient(app, base_url=base).get("/api/auth/status").status_code == 200
    ipv6 = TestClient(app, base_url="http://127.0.0.1", headers={"Host": "[::1]:8000"})
    assert ipv6.get("/api/auth/status").status_code == 200
    assert TestClient(app, base_url="http://127.0.0.1").get("/api/auth/status").json()["setup_required"] is True


def test_extra_host_names_can_be_allowed(tmp_path):
    app = make_app(tmp_path, allowed_hosts=("my-pc.local",))
    assert TestClient(app, base_url="http://my-pc.local:8000").get("/api/auth/status").status_code == 200


def test_big_bodies_refused_and_headers_set(tmp_path):
    client = TestClient(make_app(tmp_path), base_url="http://127.0.0.1")
    big = client.post("/api/auth/login", content=b"x", headers={"Content-Length": str(MAX_BODY_BYTES + 1)})
    assert big.status_code == 413
    response = client.get("/api/auth/status")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert response.headers["referrer-policy"] == "same-origin"


def test_host_name():
    assert host_name("127.0.0.1:8000") == "127.0.0.1"
    assert host_name("[::1]:8000") == "::1"
    assert host_name("LocalHost") == "localhost"
    assert host_name("") == ""
