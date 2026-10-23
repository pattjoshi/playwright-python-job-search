"""Runs auto-apply on a background thread (one run at a time), with a live log the page can poll."""

import logging
import threading
from collections.abc import Callable
from datetime import datetime

from job_search.models import Job
from job_search.services.auto_apply.boards import BOARDS
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
        # Signing in uses the same saved browser, so it also blocks a second run.
        return self.state["status"] in ("running", "stopping", "signing_in")

    def status(self) -> dict:
        return {**self.state, "logs": self.state["logs"][-50:]}

    def start(self, user_id: int, only_job: int | None = None) -> dict:
        """Work through the queue (or, with only_job, try that one job with the browser visible)."""
        self._begin("running")
        self._start_thread(lambda: self._run(user_id, only_job))
        return self.status()

    def sign_in(self, board: str) -> dict:
        """Open a visible browser on the board's sign-in page and wait while you log in."""
        if board not in BOARDS:
            raise AutoApplyError("Unknown job board.", status=404)
        self._begin("signing_in")
        self._start_thread(lambda: self._sign_in(board))
        return self.status()

    def _begin(self, status: str) -> None:
        with self._lock:
            if self.running:
                busy = "signing in" if self.state["status"] == "signing_in" else "running"
                raise AutoApplyError(f"Auto-apply is {busy}. Wait for it to finish (or press Stop).", status=409)
            self._stop.clear()
            self.state = {"status": status, "started_at": _now(), "finished_at": None, "logs": [], "applied": 0, "error": None}

    def _sign_in(self, board: str) -> None:
        try:
            problem = self.service.sign_in(board, self._say)
            self.state["error"] = problem
            if problem is None:
                self._say("Signed in. Auto-apply will stay signed in from now on.")
        except Exception as error:  # e.g. the window was closed
            log.exception("Sign-in failed")
            self.state["error"] = f"Sign-in didn't finish: {str(error).splitlines()[0] if str(error) else error.__class__.__name__}"
        finally:
            self.state["finished_at"] = _now()
            self.state["status"] = "error" if self.state["error"] else "done"

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

    def _run(self, user_id: int, only_job: int | None = None) -> None:
        try:
            self.state["applied"] = self.service.run(user_id, self._stop, self._say, only_job)
            self._say("Stopped." if self._stop.is_set() else "Done.")
        except AutoApplyError as error:
            self.state["error"] = error.message
        except Exception as error:  # show any failure on the page instead of a silent stop
            log.exception("Auto-apply failed")
            self.state["error"] = str(error) or error.__class__.__name__
        finally:
            self.service.repo.requeue_interrupted()  # a job left "Applying…" by a crash goes back in the queue
            self.state["finished_at"] = _now()
            self.state["status"] = "stopped" if self._stop.is_set() else "error" if self.state["error"] else "done"

    def _say(self, message: str) -> None:
        log.info("Auto-apply: %s", message)
        self.state["logs"] = [*self.state["logs"], f"{datetime.now():%H:%M:%S}  {message}"][-MAX_LOGS:]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
