"""Secrets saved on this computer, encrypted (Fernet: AES + HMAC).

The encryption key comes from the APP_SECRET environment variable when set, otherwise from data/secret.key,
created on first use and readable only by you. Keep APP_SECRET outside the data folder (e.g. in .env) and a copy
or backup of data/ alone no longer reveals the secrets.
"""

import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

FILE_NAME = "secrets.json"
KEY_FILE = "secret.key"


def _write_private(path: Path, text: str) -> None:
    """Write a file only its owner can read (on Windows the folder's permissions apply)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(text)
    os.replace(temp, path)


class SecretStore:
    def __init__(self, data_dir: Path, app_secret: str | None = None):
        self.path = data_dir / FILE_NAME
        self._key_path = data_dir / KEY_FILE
        self._app_secret = app_secret if app_secret is not None else os.getenv("APP_SECRET")

    def _fernet(self) -> Fernet:
        if self._app_secret:
            return Fernet(base64.urlsafe_b64encode(hashlib.sha256(self._app_secret.encode()).digest()))
        if not self._key_path.is_file():
            _write_private(self._key_path, Fernet.generate_key().decode())
        return Fernet(self._key_path.read_text(encoding="utf-8").strip().encode())

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, name: str) -> str | None:
        """The secret, or None when it isn't saved or can't be decrypted (e.g. APP_SECRET changed)."""
        token = self._read().get(name)
        if not isinstance(token, str):
            return None
        try:
            return self._fernet().decrypt(token.encode()).decode()
        except (InvalidToken, ValueError):
            return None

    def set(self, name: str, value: str) -> None:
        data = self._read()
        data[name] = self._fernet().encrypt(value.encode()).decode()
        _write_private(self.path, json.dumps(data))

    def delete(self, name: str) -> None:
        data = self._read()
        if data.pop(name, None) is not None:
            _write_private(self.path, json.dumps(data))
