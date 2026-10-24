"""The key that connects the Chrome extension to this app. Only its hash is stored (in data/auto-apply)."""

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ExtensionKeys:
    """One key at a time: connecting again replaces it (and disconnects the old one)."""

    def __init__(self, files_dir: Path):
        self.path = Path(files_dir) / "extension-key.json"

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def create(self, user_id: int) -> str:
        """A new key (shown once, to paste into the extension)."""
        key = "jsa_" + secrets.token_urlsafe(24)
        self._save({"hash": _hash(key), "user_id": user_id, "created_at": _now(), "last_seen": None})
        return key

    def user_id_for(self, key: str | None) -> int | None:
        data = self._load()
        if not key or not data.get("hash") or not secrets.compare_digest(_hash(key), data["hash"]):
            return None
        if (data.get("last_seen") or "")[:16] != _now()[:16]:  # remember when it was last used (at most once a minute)
            self._save({**data, "last_seen": _now()})
        return data.get("user_id")

    def status(self, user_id: int) -> dict:
        data = self._load()
        mine = data.get("user_id") == user_id
        return {"connected": mine and bool(data.get("hash")), "created_at": data.get("created_at") if mine else None,
                "last_seen": data.get("last_seen") if mine else None}

    def remove(self) -> None:
        self.path.unlink(missing_ok=True)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
