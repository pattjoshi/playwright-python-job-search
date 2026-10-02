"""The web page's last session, saved on disk so a page reload or app restart doesn't lose it.

data/session.json holds:
  resume    the resume you uploaded last (file path, name, and the AI's reading of it)
  last_job  the last search's final state (progress, funnel, results)

"Clear" in the UI deletes it. Settings, job history and the run history are separate and stay.
"""

import json
import threading
from dataclasses import asdict
from pathlib import Path

from job_search.models import Profile

SESSION_FILE = "session.json"


class SessionStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / SESSION_FILE
        self._lock = threading.Lock()

    def load(self) -> dict:
        with self._lock:
            return self._read()

    def save_resume(self, resume_id: str, path: Path, file_name: str, profile: Profile, suggested_experience) -> None:
        with self._lock:
            data = self._read()
            data["resume"] = {
                "resume_id": resume_id,
                "path": str(Path(path).resolve()),
                "file_name": file_name,
                "profile": asdict(profile),
                "suggested_experience": suggested_experience,
            }
            self._write(data)

    def save_last_job(self, job: dict) -> None:
        with self._lock:
            data = self._read()
            data["last_job"] = job
            self._write(data)

    def clear(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)

    def resume(self) -> dict | None:
        """The saved resume, if its file still exists (with the profile as a Profile)."""
        saved = self.load().get("resume")
        if not saved or not Path(saved.get("path", "")).is_file():
            return None
        return {**saved, "path": Path(saved["path"]), "profile": Profile(**saved["profile"])}

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}  # a damaged file just means "no saved session"
        return data if isinstance(data, dict) else {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(self.path)  # atomic: never leaves a half-written session
