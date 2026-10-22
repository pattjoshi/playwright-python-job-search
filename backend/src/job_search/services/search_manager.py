"""Runs one search at a time in a background thread, and tracks its live status."""

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from job_search.config import Settings
from job_search.models import SearchOptions
from job_search.repositories import SessionRepository
from job_search.schemas.serializers import profile_to_dict, result_to_dict
from job_search.services.matching_service import SearchStopped
from job_search.services.search import run as run_search

log = logging.getLogger(__name__)

MAX_LOG_LINES = 400


@dataclass
class SearchJob:
    id: str
    status: str = "running"  # running | stopping | done | stopped | error
    stage: str = "resume"  # resume | search | details | score | report
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    finished_at: str | None = None
    logs: list[str] = field(default_factory=list)
    sites: dict[str, dict] = field(default_factory=dict)  # site -> {"status", "found"}
    progress: dict | None = None  # {"stage", "done", "total"} for details/scoring
    funnel: list | None = None  # [[label, count], ...] jobs left after each filter
    requested: dict[str, int] = field(default_factory=dict)  # jobs to show per site
    profile: dict | None = None
    error: str | None = None
    result: dict | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)

    @property
    def active(self) -> bool:
        return self.status in ("running", "stopping")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "logs": self.logs[-MAX_LOG_LINES:],
            "sites": self.sites,
            "progress": self.progress,
            "funnel": self.funnel,
            "requested": self.requested,
            "profile": self.profile,
            "error": self.error,
            "result": self.result,
        }

    def on_event(self, name: str, data: dict) -> None:
        if name == "stage":
            self.stage = data["stage"]
            self.progress = None
        elif name == "profile":
            self.profile = profile_to_dict(data["profile"], data["queries"], data["locations"])
        elif name == "site":
            self.sites[data["site"]] = {"status": data["status"], "found": data["found"]}
        elif name == "progress":
            self.progress = data
        elif name == "funnel":
            self.funnel = [list(step) for step in data["steps"]]


class _JobLogHandler(logging.Handler):
    """Copies log lines from the search into the job, so the page can show details."""

    def __init__(self, job: SearchJob):
        super().__init__(level=logging.INFO)
        self.job = job
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        self.job.logs.append(self.format(record))
        del self.job.logs[:-MAX_LOG_LINES]


class SearchManager:
    """Runs one search at a time in a background thread (one browser is plenty)."""

    def __init__(self, settings: Settings, output_dir: Path, runner=run_search, session: SessionRepository | None = None):
        self.settings = settings
        self.output_dir = output_dir
        self.runner = runner
        self.session = session
        self.jobs: dict[str, SearchJob] = {}
        self._lock = threading.Lock()
        self._current: SearchJob | None = None

    @property
    def running(self) -> SearchJob | None:
        return self._current if self._current and self._current.active else None

    def start(self, options: SearchOptions, sites: list[str]) -> SearchJob:
        with self._lock:
            if self.running:
                raise RuntimeError("A search is already running. Stop it or wait for it to finish.")
            job = SearchJob(
                id=uuid.uuid4().hex[:12],
                sites={site: {"status": "waiting", "found": 0} for site in sites},
                requested={site: options.results_per_site.get(site, options.results) for site in sites},
            )
            self.jobs[job.id] = job
            self._current = job
        threading.Thread(target=self._run, args=(job, options), daemon=True).start()
        return job

    def stop(self, job: SearchJob) -> None:
        if job.status == "running":
            job.status = "stopping"
            job.logs.append("Stopping…")
            job.stop_event.set()

    def _run(self, job: SearchJob, options: SearchOptions) -> None:
        handler = _JobLogHandler(job)
        package_logger = logging.getLogger(__name__.split(".")[0])
        if package_logger.getEffectiveLevel() > logging.INFO:
            package_logger.setLevel(logging.INFO)
        package_logger.addHandler(handler)
        try:
            result = self.runner(options, self.settings, on_event=job.on_event, stop_event=job.stop_event)
            job.result = result_to_dict(result, self.output_dir)
            job.status = "done"
            job.logs.append("Done.")
        except SearchStopped:
            job.status = "stopped"
            job.logs.append("Stopped.")
        except Exception as error:  # show any failure on the page instead of a silent stop
            log.exception("Search failed")
            job.error = str(error) or error.__class__.__name__
            job.status = "error"
        finally:
            package_logger.removeHandler(handler)
            job.finished_at = datetime.now().isoformat(timespec="seconds")
            if self.session:
                try:
                    # Kept so a page reload (or app restart) shows this search again.
                    self.session.save_last_job({**job.to_dict(), "logs": job.logs[-100:]})
                except Exception:
                    log.exception("Couldn't save the session")
