"""Password hashing with scrypt (Python's standard library): slow on purpose, salted, constant-time check."""

import base64
import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1  # scrypt cost: ~16 MB and a few tens of ms per check
MIN_LENGTH = 8


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def password_problem(password: str) -> str | None:
    """A friendly reason the password is too weak, or None when it's fine."""
    if len(password) < MIN_LENGTH:
        return f"Use at least {MIN_LENGTH} characters for the password."
    if password.isdigit() or password.lower() in ("password", "password1", "12345678", "qwertyui"):
        return "That password is too easy to guess."
    return None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()
