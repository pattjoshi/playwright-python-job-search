"""`python -m job_search daily`: run the saved daily search (started by Task Scheduler / cron)."""

import logging
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from job_search.cli.logs import setup_logging
from job_search.config import load_settings
from job_search.repositories import LOG_FILE, load_schedule, save_state
from job_search.services.cleanup_service import cleanup
from job_search.services.openai_key import with_saved_key
from job_search.services.schedule_service import options_from_dict
from job_search.services.search import run

log = logging.getLogger(__name__)


def main(_argv: list[str] | None = None) -> int:
    settings = with_saved_key(load_settings())
    data_dir = settings.history_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(data_dir / LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stderr)]
    setup_logging(datefmt="%Y-%m-%d %H:%M:%S", handlers=handlers)

    schedule = load_schedule(data_dir)
    if schedule is None:
        log.error("No daily search is saved. Set one up in the web UI first.")
        return 1

    started = datetime.now().isoformat(timespec="seconds")
    log.info("Daily search started")
    options = options_from_dict(schedule.search)
    options.origin = "daily"
    options.parallel_sites = settings.parallel_sites
    try:
        result = run(options, settings)
    except Exception as error:  # record any failure so the UI can show it
        log.exception("Daily search failed")
        save_state(data_dir, last_run=started, status="error", error=str(error) or error.__class__.__name__)
        return 1

    shown = sum(len(jobs) for jobs in result.top_by_site.values())
    new = sum(1 for jobs in result.top_by_site.values() for job in jobs if job.is_new)
    save_state(
        data_dir, last_run=started, status="done", jobs=shown, new=new, report=str(Path(result.html_path).resolve()),
        duration_s=result.stats.duration_s, cost_usd=result.stats.cost_usd,
    )
    log.info("Daily search finished: %d jobs (%d new). Report: %s", shown, new, result.html_path)
    if schedule.open_report:
        webbrowser.open(Path(result.html_path).resolve().as_uri())
    try:
        cleanup(settings.keep_days, data_dir, Path(options.resume_path).parent, options.output_dir, settings.cache_path)
    except Exception:  # housekeeping must never fail the daily run
        log.exception("Cleanup failed")
    return 0

