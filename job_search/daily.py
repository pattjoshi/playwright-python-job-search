"""Runs the saved daily search. The OS scheduler calls:  python -m job_search.daily

Results go to the usual HTML/Excel reports; the HTML report opens in your browser
when it's ready (unless turned off). Progress is logged to data/scheduled.log.
"""

import logging
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from job_search.cleanup import cleanup
from job_search.config import load_settings
from job_search.pipeline import run
from job_search.schedule import LOG_FILE, load_schedule, options_from_dict, save_state

log = logging.getLogger("job_search.daily")


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    data_dir = settings.history_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(data_dir / LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )
    for noisy in ("httpx", "openai", "pdfminer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

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


if __name__ == "__main__":
    raise SystemExit(main())
