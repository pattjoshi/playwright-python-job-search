"""Accounts and sign-in: first-run setup, sign in/out, current user, password change."""

import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from job_search.repositories.user_repository import User, UserRepository
from job_search.services.auth.passwords import hash_password, password_problem, verify_password
from job_search.services.auth.throttle import LoginThrottle

SESSION_DAYS = 30
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


class AuthService:
    def __init__(self, users: UserRepository, throttle: LoginThrottle | None = None):
        self.users = users
        self.throttle = throttle or LoginThrottle()

    def setup_required(self) -> bool:
        return self.users.count() == 0

    def create_owner(self, name: str, email: str, password: str) -> tuple[User, str]:
        """First run only: create the owner account and sign it in. Returns (user, session token)."""
        if not self.setup_required():
            raise AuthError("An account already exists. Sign in instead.", 409)
        name, email = " ".join(name.split())[:80], email.strip()
        if not _EMAIL.match(email):
            raise AuthError("Enter a valid email address.")
        if problem := password_problem(password):
            raise AuthError(problem)
        try:
            user = self.users.create(email, name, hash_password(password), role="owner")
        except (IntegrityError, sqlite3.IntegrityError):
            raise AuthError("An account already exists. Sign in instead.", 409) from None
        return user, self._start_session(user)

    def sign_in(self, email: str, password: str, client: str) -> tuple[User, str]:
        key = f"{client}|{email.strip().lower()}"
        if wait := self.throttle.retry_after(key):
            raise AuthError(f"Too many tries. Wait {wait} seconds and try again.", 429)
        found = self.users.credentials(email.strip())
        if not found or not verify_password(password, found[1]):
            self.throttle.failed(key)
            raise AuthError("Wrong email or password.", 401)
        self.throttle.succeeded(key)
        return found[0], self._start_session(found[0])

    def user_for(self, token: str | None) -> User | None:
        if not token:
            return None
        return self.users.session_user(_token_hash(token), _now().isoformat())

    def sign_out(self, token: str | None) -> None:
        if token:
            self.users.remove_session(_token_hash(token))

    def change_password(self, user: User, current: str, new: str, token: str | None) -> None:
        """Change the password and sign out every other browser."""
        stored = self.users.password_hash(user.id)
        if not stored or not verify_password(current, stored):
            raise AuthError("Your current password isn't right.", 403)
        if problem := password_problem(new):
            raise AuthError(problem)
        self.users.set_password_hash(user.id, hash_password(new))
        self.users.remove_sessions(user.id, keep=_token_hash(token) if token else None)

    def sign_out_everywhere(self, user: User) -> None:
        self.users.remove_sessions(user.id)

    def reset_password(self, email: str, new: str) -> User:
        """For the command line (someone at the computer): set a new password without the old one."""
        found = self.users.credentials(email)
        if not found:
            raise AuthError(f"No account with the email {email}.", 404)
        if problem := password_problem(new):
            raise AuthError(problem)
        self.users.set_password_hash(found[0].id, hash_password(new))
        self.users.remove_sessions(found[0].id)
        return found[0]

    def _start_session(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        self.users.remove_expired_sessions(now.isoformat())
        self.users.add_session(_token_hash(token), user.id, (now + timedelta(days=SESSION_DAYS)).isoformat())
        return token
