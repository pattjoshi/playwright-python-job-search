"""Passwords, sessions, throttling and the reset-password command (no web server)."""

import pytest

import job_search.cli.reset_password as reset_cli
from job_search.config import Settings
from job_search.repositories import UserRepository
from job_search.services.auth import AuthError, AuthService, LoginThrottle
from job_search.services.auth.passwords import hash_password, password_problem, verify_password


def test_password_hashing():
    stored = hash_password("correct horse battery")
    assert stored.startswith("scrypt$") and "correct" not in stored
    assert stored != hash_password("correct horse battery")  # salted
    assert verify_password("correct horse battery", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("anything", "not-a-hash")
    assert password_problem("short") and password_problem("12345678901") and password_problem("password")
    assert password_problem("correct horse battery") is None


def test_throttle_blocks_after_repeated_failures_then_lets_through():
    now = [0.0]
    throttle = LoginThrottle(max_failures=3, window_s=60, clock=lambda: now[0])
    for _ in range(3):
        throttle.failed("me")
    assert throttle.retry_after("me") > 0
    now[0] = 61
    assert throttle.retry_after("me") == 0


def test_sessions_and_password_change(tmp_path):
    auth = AuthService(UserRepository(tmp_path / "h.sqlite3"))
    user, first = auth.create_owner("Om", "om@example.com", "correct horse battery")
    _, second = auth.sign_in("OM@example.com ", "correct horse battery", "1.2.3.4")  # email case and spaces don't matter

    assert auth.user_for(first) == user and auth.user_for("made-up") is None
    with pytest.raises(AuthError, match="current password"):
        auth.change_password(user, "wrong", "another long one", first)
    auth.change_password(user, "correct horse battery", "another long one", first)
    assert auth.user_for(first) == user  # this browser stays signed in
    assert auth.user_for(second) is None  # others are signed out
    auth.sign_out(first)
    assert auth.user_for(first) is None


def test_expired_session_is_refused(tmp_path):
    users = UserRepository(tmp_path / "h.sqlite3")
    user = users.create("om@example.com", "Om", hash_password("correct horse battery"), "owner")
    users.add_session("hash-of-old-token", user.id, "2000-01-01T00:00:00")
    assert users.session_user("hash-of-old-token", "2026-01-01T00:00:00") is None


def test_reset_password_command(tmp_path, monkeypatch, capsys):
    path = tmp_path / "h.sqlite3"
    AuthService(UserRepository(path)).create_owner("Om", "om@example.com", "correct horse battery")
    monkeypatch.setattr(reset_cli, "load_settings", lambda: Settings("key", history_path=path))

    answers = iter(["brand new password", "brand new password"])
    assert reset_cli.main(["--email", "om@example.com"], read_password=lambda _prompt: next(answers)) == 0
    assert AuthService(UserRepository(path)).sign_in("om@example.com", "brand new password", "x")[0].email == "om@example.com"

    mismatch = iter(["one long password", "two long password"])
    assert reset_cli.main(["--email", "om@example.com"], read_password=lambda _prompt: next(mismatch)) == 1
    assert "don't match" in capsys.readouterr().err
