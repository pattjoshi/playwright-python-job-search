"""Local web UI: upload a resume, pick how many jobs per site, watch the search run.

Start it with:  python -m job_search.web   (then it opens http://127.0.0.1:8000)

It only listens on your own computer (127.0.0.1), never on the network.
"""

import argparse
import logging
import threading
import uuid
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from job_search.config import Settings, load_settings
from job_search.html_report import SITE_NAMES
from job_search.models import Job, Profile
from job_search.pipeline import SearchOptions, SearchResult, run
from job_search.resume import SUPPORTED_SUFFIXES
from job_search.scrapers import SCRAPERS

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_LOG_LINES = 400
MAX_RESULTS = 100


@dataclass
class SearchJob:
    id: str
    status: str = "running"  # running | done | error
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    logs: list[str] = field(default_factory=list)
    profile: dict | None = None
    error: str | None = None
    result: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "started_at": self.started_at,
            "logs": self.logs[-MAX_LOG_LINES:],
            "profile": self.profile,
            "error": self.error,
            "result": self.result,
        }


class _JobLogHandler(logging.Handler):
    """Copies log lines from the search into the job, so the page can show progress."""

    def __init__(self, job: SearchJob):
        super().__init__(level=logging.INFO)
        self.job = job
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        self.job.logs.append(self.format(record))
        del self.job.logs[:-MAX_LOG_LINES]


class SearchManager:
    """Runs one search at a time in a background thread (one browser is plenty)."""

    def __init__(self, settings: Settings, output_dir: Path, runner=run):
        self.settings = settings
        self.output_dir = output_dir
        self.runner = runner
        self.jobs: dict[str, SearchJob] = {}
        self._lock = threading.Lock()
        self._running: SearchJob | None = None

    @property
    def running(self) -> SearchJob | None:
        return self._running if self._running and self._running.status == "running" else None

    def start(self, options: SearchOptions) -> SearchJob:
        with self._lock:
            if self.running:
                raise RuntimeError("A search is already running. Wait for it to finish.")
            job = SearchJob(id=uuid.uuid4().hex[:12])
            self.jobs[job.id] = job
            self._running = job
        threading.Thread(target=self._run, args=(job, options), daemon=True).start()
        return job

    def _run(self, job: SearchJob, options: SearchOptions) -> None:
        handler = _JobLogHandler(job)
        package_logger = logging.getLogger("job_search")
        if package_logger.getEffectiveLevel() > logging.INFO:
            package_logger.setLevel(logging.INFO)
        package_logger.addHandler(handler)

        def on_profile(profile: Profile, queries: list[str], locations: list[str]) -> None:
            job.profile = profile_to_dict(profile, queries, locations)

        try:
            result = self.runner(options, self.settings, on_profile=on_profile)
            job.result = result_to_dict(result, self.output_dir)
            job.status = "done"
            job.logs.append("Done.")
        except Exception as error:  # show any failure on the page instead of a silent stop
            log.exception("Search failed")
            job.error = str(error) or error.__class__.__name__
            job.status = "error"
        finally:
            package_logger.removeHandler(handler)


def create_app(settings: Settings | None = None, output_dir: Path = Path("output"), upload_dir: Path = Path("uploads"), runner=run) -> Flask:
    settings = settings or load_settings()
    manager = SearchManager(settings, output_dir, runner)
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.extensions["search_manager"] = manager

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/api/config")
    def config():
        return jsonify(
            {
                "sites": [
                    {"id": site, "name": SITE_NAMES.get(site, site.title()), "results": settings.results_per_site.get(site, settings.results)}
                    for site in SCRAPERS
                ],
                "enabled_sites": settings.sites or list(SCRAPERS),
                "location": settings.location or "",
                "keywords": ", ".join(settings.keywords),
                "hours": settings.hours,
                "has_api_key": bool(settings.openai_api_key),
                "running_job": manager.running.id if manager.running else None,
                "resume_types": list(SUPPORTED_SUFFIXES),
            }
        )

    @app.post("/api/search")
    def start_search():
        if not settings.openai_api_key:
            return _error("OPENAI_API_KEY is not set. Add it to your .env file and restart the app.")

        upload = request.files.get("resume")
        if upload is None or not upload.filename:
            return _error("Choose your resume file first.")
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            return _error(f"Resume must be one of: {', '.join(SUPPORTED_SUFFIXES)}")

        sites, results_per_site = [], {}
        for site in SCRAPERS:
            if request.form.get(f"site_{site}") != "on":
                continue
            count = _form_int(f"results_{site}", default=10)
            if count is None or not 1 <= count <= MAX_RESULTS:
                return _error(f"Jobs to show for {SITE_NAMES.get(site, site)} must be between 1 and {MAX_RESULTS}.")
            sites.append(site)
            results_per_site[site] = count
        if not sites:
            return _error("Pick at least one job site.")

        hours = _form_int("hours", default=settings.hours)
        if hours is None or not 1 <= hours <= 24 * 30:
            return _error("'Posted within' must be between 1 and 720 hours.")

        upload_dir.mkdir(parents=True, exist_ok=True)
        resume_path = upload_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{secure_filename(upload.filename) or 'resume' + suffix}"
        upload.save(resume_path)

        keywords = [k.strip() for k in request.form.get("keywords", "").split(",") if k.strip()]
        options = SearchOptions(
            resume_path=resume_path,
            sites=sites,
            location=request.form.get("location", "").strip() or None,
            keywords=keywords,
            max_age_hours=hours,
            max_pages=settings.max_pages,
            top_n=settings.top,
            results=settings.results,
            results_per_site=results_per_site,
            use_llm=True,
            headless=request.form.get("show_browser") != "on",
            output_dir=output_dir,
        )
        try:
            job = manager.start(options)
        except RuntimeError as error:
            return _error(str(error), status=409)
        return jsonify({"id": job.id}), 202

    @app.get("/api/search/<job_id>")
    def search_status(job_id: str):
        job = manager.jobs.get(job_id)
        if job is None:
            abort(404)
        return jsonify(job.to_dict())

    @app.get("/reports/<path:name>")
    def report(name: str):
        return send_from_directory(output_dir.resolve(), name)

    @app.errorhandler(413)
    def too_large(_error):
        return _error(f"Resume file is too big (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).", status=413)

    return app


def profile_to_dict(profile: Profile, queries: list[str], locations: list[str]) -> dict:
    return {
        "summary": profile.summary,
        "current_title": profile.current_title,
        "skills": profile.skills,
        "years_experience": profile.years_experience,
        "keywords": queries,
        "locations": locations,
    }


def job_to_dict(job: Job) -> dict:
    return {
        "source": job.source,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "posted_text": job.posted_text,
        "score": job.score,
        "match_reason": job.match_reason,
        "matched_skills": job.matched_skills,
        "missing_skills": job.missing_skills,
    }


def result_to_dict(result: SearchResult, output_dir: Path) -> dict:
    def report_url(path: Path) -> str:
        return f"/reports/{path.resolve().relative_to(output_dir.resolve()).as_posix()}"

    return {
        "sites": [
            {"id": site, "name": SITE_NAMES.get(site, site.title()), "jobs": [job_to_dict(job) for job in jobs]}
            for site, jobs in result.top_by_site.items()
        ],
        "scored": len(result.jobs),
        "html_report": report_url(result.html_path),
        "excel_report": report_url(result.xlsx_path),
    }


def _form_int(name: str, default: int) -> int | None:
    value = request.form.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return None


def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job_search.web", description="Open the job search web UI.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="Don't open the browser automatically")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("httpx", "openai", "pdfminer", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    try:
        app = create_app()
    except ValueError as error:  # e.g. a bad number in .env
        logging.error("%s", error)
        return 1

    url = f"http://127.0.0.1:{args.port}"
    print(f"\n  Job search is running at {url}\n  Press Ctrl+C to stop.\n")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    app.run(host="127.0.0.1", port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
