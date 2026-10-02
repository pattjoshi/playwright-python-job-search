"""Local web UI: upload a resume, tune the search, watch it run, act on the results.

Start it with:  python -m job_search.web   (then it opens http://127.0.0.1:8000)

It only listens on your own computer (127.0.0.1), never on the network.
"""

import argparse
import logging
import math
import threading
import uuid
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from job_search.cache import Cache, resume_key
from job_search.cleanup import cleanup
from job_search.config import Settings, load_settings
from job_search.history import STATUSES, JobHistory
from job_search.html_report import SITE_NAMES
from job_search.llm import JobMatcherLLM
from job_search.locations import LOCATION_CHOICES, normalize_location
from job_search.models import Job, Profile
from job_search.pipeline import SearchOptions, SearchResult, run
from job_search.resume import SUPPORTED_SUFFIXES, read_resume_text
from job_search.schedule import (
    Schedule,
    ScheduleError,
    SystemScheduler,
    clean_days,
    delete_schedule,
    load_schedule,
    load_state,
    options_to_dict,
    parse_time,
    save_schedule,
)
from job_search.scrapers import SCRAPERS
from job_search.session import SessionStore
from job_search.utils import SearchStopped

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_LOG_LINES = 400
MAX_RESULTS = 100


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

    def __init__(self, settings: Settings, output_dir: Path, runner=run, session: SessionStore | None = None):
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
        package_logger = logging.getLogger("job_search")
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


def default_analyzer(settings: Settings):
    def analyze(resume_path: Path) -> Profile:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file and restart the app.")
        # The same resume file (by content) is only sent to the AI once.
        cache = Cache(settings.cache_path)
        key = resume_key(resume_path, settings.openai_model)
        profile = cache.get_profile(key)
        if profile is None:
            text = read_resume_text(resume_path)
            profile = JobMatcherLLM(settings.openai_api_key, settings.openai_model).extract_profile(text)
            cache.save_profile(key, profile)
        return profile

    return analyze


def create_app(
    settings: Settings | None = None,
    output_dir: Path = Path("output"),
    upload_dir: Path = Path("uploads"),
    runner=run,
    analyzer=None,
    system_scheduler: SystemScheduler | None = None,
) -> Flask:
    settings = settings or load_settings()
    analyzer = analyzer or default_analyzer(settings)
    data_dir = settings.history_path.parent
    scheduler = system_scheduler or SystemScheduler(data_dir)
    try:
        cleanup(settings.keep_days, data_dir, upload_dir, output_dir, settings.cache_path)
    except Exception:  # housekeeping must never stop the app from starting
        log.exception("Cleanup failed")
    session = SessionStore(data_dir)
    manager = SearchManager(settings, output_dir, runner, session)
    history = JobHistory(settings.history_path)
    resumes: dict[str, dict] = {}  # resume_id -> {"path", "name", "profile"}
    saved = session.resume()
    if saved:  # the resume from before a restart still works without uploading it again
        resumes[saved["resume_id"]] = {"path": saved["path"], "name": saved["file_name"], "profile": saved["profile"]}

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
                    {
                        "id": site,
                        "name": SITE_NAMES.get(site, site.title()),
                        "results": settings.results_per_site.get(site, settings.results),
                    }
                    for site in SCRAPERS
                ],
                "enabled_sites": settings.sites or list(SCRAPERS),
                "location_choices": LOCATION_CHOICES,
                "defaults": {
                    "locations": settings.locations,
                    "keywords": settings.keywords,
                    "hours": settings.hours,
                    "experience": list(settings.experience) if settings.experience else None,
                    "only_new": settings.only_new,
                    "max_pages": settings.max_pages,
                    "top": settings.top,
                    "parallel_sites": settings.parallel_sites,
                },
                "has_api_key": bool(settings.openai_api_key),
                "running_job": manager.running.id if manager.running else None,
                "resume_types": list(SUPPORTED_SUFFIXES),
                "history": history.counts(),
            }
        )

    @app.post("/api/analyze")
    def analyze():
        upload = request.files.get("resume")
        if upload is None or not upload.filename:
            return _error("Choose your resume file first.")
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            return _error(f"Resume must be one of: {', '.join(SUPPORTED_SUFFIXES)}")

        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = secure_filename(upload.filename) or f"resume{suffix}"
        path = upload_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{safe_name}"
        upload.save(path)
        try:
            profile = analyzer(path)
        except Exception as error:  # unreadable file, OpenAI error, missing key...
            log.warning("Could not read resume: %s", error)
            return _error(f"Could not read your resume: {error}")

        resume_id = uuid.uuid4().hex[:12]
        resumes[resume_id] = {"path": path, "name": upload.filename, "profile": profile}
        suggested = suggest_experience(profile.years_experience)
        session.save_resume(resume_id, path, upload.filename, profile, suggested)
        return jsonify(resume_to_dict(resume_id, upload.filename, profile, suggested))

    @app.get("/api/session")
    def get_session():
        """What the page showed before a reload: the resume and the last search."""
        data = session.load()
        saved = session.resume()
        resume = resume_to_dict(saved["resume_id"], saved["file_name"], saved["profile"], saved.get("suggested_experience")) if saved else None
        last_job = data.get("last_job")
        if last_job and last_job.get("result"):
            # Show jobs you marked applied/hidden since then as such.
            jobs = [
                Job(j["source"], j["job_id"], j.get("title", ""), "", "", "")
                for site in last_job["result"]["sites"] for j in site["jobs"]
            ]
            statuses = history.statuses(jobs)
            for site in last_job["result"]["sites"]:
                for j in site["jobs"]:
                    j["status"] = statuses.get((j["source"], j["job_id"]))
        return jsonify({"resume": resume, "last_job": last_job})

    @app.post("/api/session/clear")
    def clear_session():
        if manager.running:
            return _error("Stop the running search before clearing.", status=409)
        saved = session.load().get("resume")
        if saved:
            resumes.pop(saved.get("resume_id"), None)
        session.clear()
        return jsonify({"resume": None, "last_job": None})

    @app.post("/api/search")
    def start_search():
        if not settings.openai_api_key:
            return _error("OPENAI_API_KEY is not set. Add it to your .env file and restart the app.")
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _error("Send the search settings as JSON.")
        resume = resumes.get(str(body.get("resume_id", "")))
        if resume is None:
            return _error("Upload your resume first (or again, if the app was restarted).")

        try:
            options, sites = _search_options(body, resume)
        except ValueError as error:
            return _error(str(error))
        try:
            job = manager.start(options, sites)
        except RuntimeError as error:
            return _error(str(error), status=409)
        return jsonify({"id": job.id}), 202

    def _search_options(body: dict, resume: dict) -> tuple[SearchOptions, list[str]]:
        site_counts = body.get("sites")
        if not isinstance(site_counts, dict) or not site_counts:
            raise ValueError("Pick at least one job site.")
        results_per_site = {}
        for site, count in site_counts.items():
            if site not in SCRAPERS:
                raise ValueError(f"Unknown job site: {site}")
            name = SITE_NAMES.get(site, site)
            results_per_site[site] = _int(count, f"Jobs to show for {name}", 1, MAX_RESULTS)
        sites = [site for site in SCRAPERS if site in results_per_site]

        experience = body.get("experience")
        if experience is not None:
            if not (isinstance(experience, list) and len(experience) == 2):
                raise ValueError("Experience must be a 'from' and a 'to' number of years.")
            low = _int(experience[0], "Experience from", 0, 50)
            high = _int(experience[1], "Experience to", 0, 50)
            if low > high:
                raise ValueError("Experience 'from' can't be more than 'to'.")
            experience = (low, high)

        return (
            SearchOptions(
                resume_path=resume["path"],
                sites=sites,
                locations=_str_list(body.get("locations"), "locations", max_items=10),
                keywords=_str_list(body.get("keywords"), "keywords", max_items=8),
                experience=experience,
                max_age_hours=_int(body.get("hours", settings.hours), "Posted within (hours)", 1, 24 * 30),
                max_pages=_int(body.get("max_pages", settings.max_pages), "Pages per search", 1, 10),
                top_n=_int(body.get("top", settings.top), "Jobs to score per site", 5, 200),
                results=settings.results,
                results_per_site=results_per_site,
                only_new=bool(body.get("only_new", False)),
                history_path=settings.history_path,
                cache_path=settings.cache_path,
                parallel_sites=settings.parallel_sites,
                origin="web",
                profile=resume["profile"],
                use_llm=True,
                headless=not body.get("show_browser", True),
                output_dir=output_dir,
            ),
            sites,
        )

    @app.get("/api/search/<job_id>")
    def search_status(job_id: str):
        return jsonify(_job(job_id).to_dict())

    @app.post("/api/search/<job_id>/stop")
    def stop_search(job_id: str):
        job = _job(job_id)
        manager.stop(job)
        return jsonify(job.to_dict())

    @app.post("/api/jobs/status")
    def set_job_status():
        body = request.get_json(silent=True) or {}
        source, job_id, status = (str(body.get(key, "")) for key in ("source", "job_id", "status"))
        if source not in SCRAPERS or not job_id or status not in STATUSES:
            return _error(f"Need a known source, a job_id and a status ({', '.join(STATUSES)}).")
        history.set_status(
            source, job_id, status,
            title=str(body.get("title", ""))[:300], company=str(body.get("company", ""))[:200], url=str(body.get("url", ""))[:1000],
        )
        return jsonify({"ok": True, "history": history.counts()})

    @app.get("/api/history")
    def list_history():
        status = request.args.get("status", "applied")
        if status not in STATUSES:
            return _error(f"status must be one of {', '.join(STATUSES)}")
        return jsonify({"jobs": history.list_jobs(status), "history": history.counts()})

    @app.get("/api/runs")
    def list_runs():
        runs = history.list_runs(limit=50)
        for item in runs:
            report = item.get("report")
            item["report_url"] = None
            if report:
                try:
                    relative = Path(report).resolve().relative_to(output_dir.resolve())
                    if (output_dir / relative).exists():
                        item["report_url"] = f"/reports/{relative.as_posix()}"
                except ValueError:
                    pass
        return jsonify({"runs": runs, "costs_configured": settings.price_input is not None and settings.price_output is not None})

    @app.post("/api/history/forget")
    def forget_history():
        forgotten = history.forget_seen()
        return jsonify({"forgotten": forgotten, "history": history.counts()})

    def schedule_status() -> dict:
        schedule = load_schedule(data_dir)
        state = load_state(data_dir)
        if state and state.get("report"):
            try:
                relative = Path(state["report"]).resolve().relative_to(output_dir.resolve())
                state["report_url"] = f"/reports/{relative.as_posix()}"
            except ValueError:
                pass
        summary = None
        if schedule:
            search = schedule.search
            summary = {
                "time": schedule.time,
                "days": schedule.days,
                "open_report": schedule.open_report,
                "next_run": schedule.next_run().isoformat(timespec="minutes"),
                "sites": search.get("results_per_site", {}),
                "keywords": search.get("keywords", []),
                "locations": search.get("locations", []),
                "experience": search.get("experience"),
                "hours": search.get("max_age_hours"),
                "resume": Path(search.get("resume_path", "")).name,
                "saved_at": schedule.saved_at,
            }
        return {"supported": scheduler.kind != "unsupported", "kind": scheduler.kind, "schedule": summary, "last_run": state}

    @app.get("/api/schedule")
    def get_schedule():
        return jsonify(schedule_status())

    @app.post("/api/schedule")
    def set_schedule():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _error("Send the schedule as JSON.")
        resume = resumes.get(str(body.get("resume_id", "")))
        if resume is None:
            return _error("Upload your resume first (or again, if the app was restarted).")
        try:
            parse_time(str(body.get("time", "")))
            options, _sites = _search_options(body, resume)
            schedule = Schedule(
                time=str(body["time"]).strip(),
                days=clean_days(body.get("days")),
                open_report=bool(body.get("open_report", True)),
                search=options_to_dict(options),
            )
        except ValueError as error:
            return _error(str(error))
        try:
            scheduler.install(schedule)
        except ScheduleError as error:
            return _error(f"Couldn't set up the daily search: {error}", status=500)
        save_schedule(data_dir, schedule)
        return jsonify(schedule_status())

    @app.delete("/api/schedule")
    def remove_schedule():
        try:
            scheduler.remove()
        except ScheduleError as error:
            return _error(f"Couldn't remove the daily search: {error}", status=500)
        delete_schedule(data_dir)
        return jsonify(schedule_status())

    @app.get("/reports/<path:name>")
    def report(name: str):
        return send_from_directory(output_dir.resolve(), name)

    @app.errorhandler(413)
    def too_large(_error):
        return _error(f"Resume file is too big (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).", status=413)

    def _job(job_id: str) -> SearchJob:
        job = manager.jobs.get(job_id)
        if job is None:
            abort(404)
        return job

    return app


def suggest_experience(years: float | None) -> list[int] | None:
    """A sensible starting range around the resume's experience: 4 years -> [3, 5]."""
    if years is None or years < 0:
        return None
    return [max(0, math.floor(years) - 1), min(50, math.ceil(years) + 1)]


def resume_to_dict(resume_id: str, file_name: str, profile: Profile, suggested_experience) -> dict:
    locations = []
    for location in profile.locations:
        city = normalize_location(location)
        if city and city not in locations:
            locations.append(city)
    return {
        "resume_id": resume_id,
        "file_name": file_name,
        "profile": profile_to_dict(profile, profile.search_queries or profile.target_titles, locations),
        "suggested_experience": suggested_experience,
    }


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
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "posted_text": job.posted_text,
        "experience": job.experience,
        "is_new": job.is_new,
        "score": job.score,
        "match_reason": job.match_reason,
        "matched_skills": job.matched_skills,
        "missing_skills": job.missing_skills,
    }


def result_to_dict(result: SearchResult, output_dir: Path) -> dict:
    def report_url(path: Path) -> str:
        return f"/reports/{path.resolve().relative_to(output_dir.resolve()).as_posix()}"

    stats = result.stats
    return {
        "sites": [
            {"id": site, "name": SITE_NAMES.get(site, site.title()), "jobs": [job_to_dict(job) for job in jobs]}
            for site, jobs in result.top_by_site.items()
        ],
        "scored": len(result.jobs),
        "stats": {
            "duration_s": stats.duration_s,
            "ai_calls": stats.usage.calls,
            "tokens": stats.usage.input_tokens + stats.usage.output_tokens,
            "cached_tokens": stats.usage.cached_tokens,
            "cost_usd": stats.cost_usd,
            "scores_reused": stats.scores_reused,
            "descriptions_reused": stats.descriptions_reused,
        },
        "html_report": report_url(result.html_path),
        "excel_report": report_url(result.xlsx_path),
    }


def _int(value, label: str, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a whole number.") from None
    if not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    return number


def _str_list(value, label: str, max_items: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    items = []
    for item in value:
        text = " ".join(str(item).split())[:80]
        if text and text not in items:
            items.append(text)
    if len(items) > max_items:
        raise ValueError(f"Use at most {max_items} {label}.")
    return items


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
    except ValueError as error:  # e.g. a bad value in .env
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
