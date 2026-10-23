"""Runs auto-apply on a background thread (one run at a time), with a live log the page can poll."""

import logging
import threading
from collections.abc import Callable
from datetime import datetime

from job_search.models import Job
from job_search.services.auto_apply.service import AutoApplyError, AutoApplyService

log = logging.getLogger(__name__)
MAX_LOGS = 200


class AutoApplyManager:
    def __init__(self, service: AutoApplyService, start_thread: Callable[[Callable[[], None]], None] | None = None):
        self.service = service
        self._start_thread = start_thread or (lambda target: threading.Thread(target=target, daemon=True).start())
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.state = {"status": "idle", "started_at": None, "finished_at": None, "logs": [], "applied": 0, "error": None}

    @property
    def running(self) -> bool:
        return self.state["status"] in ("running", "stopping")

    def status(self) -> dict:
        return {**self.state, "logs": self.state["logs"][-50:]}

    def start(self, user_id: int) -> dict:
        with self._lock:
            if self.running:
                raise AutoApplyError("Auto-apply is already running.", status=409)
            self._stop.clear()
            self.state = {"status": "running", "started_at": _now(), "finished_at": None, "logs": [], "applied": 0, "error": None}
        self._start_thread(lambda: self._run(user_id))
        return self.status()

    def stop(self) -> dict:
        if self.state["status"] == "running":
            self.state["status"] = "stopping"
            self._say("Stopping after the current job…")
            self._stop.set()
        return self.status()

    def after_search(self, user_id: int, jobs: list[Job]) -> int:
        """Queue a finished search's matches; start applying if you asked for that."""
        try:
            added = self.service.queue_jobs(user_id, jobs)
            if added:
                log.info("Added %d job%s to the auto-apply queue", added, "" if added == 1 else "s")
            if self.service.repo.settings(user_id)["run_after_search"] and not self.running:
                self.start(user_id)
            return added
        except Exception:  # queueing must never break the search that just finished
            log.exception("Couldn't queue jobs for auto-apply")
            return 0

    def _run(self, user_id: int) -> None:
        try:
            self.state["applied"] = self.service.run(user_id, self._stop, self._say)
            self._say("Stopped." if self._stop.is_set() else "Done.")
        except AutoApplyError as error:
            self.state["error"] = error.message
        except Exception as error:  # show any failure on the page instead of a silent stop
            log.exception("Auto-apply failed")
            self.state["error"] = str(error) or error.__class__.__name__
        finally:
            self.state["finished_at"] = _now()
            self.state["status"] = "stopped" if self._stop.is_set() else "error" if self.state["error"] else "done"

    def _say(self, message: str) -> None:
        log.info("Auto-apply: %s", message)
        self.state["logs"] = [*self.state["logs"], f"{datetime.now():%H:%M:%S}  {message}"][-MAX_LOGS:]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
