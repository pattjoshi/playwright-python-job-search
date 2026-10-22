"""Entry point of a search: runs the pipeline, times it and saves it in the run history."""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from job_search.config import Settings
from job_search.models import RunStats, SearchOptions, SearchResult
from job_search.repositories import JobHistoryRepository
from job_search.services.matching_service import SearchStopped
from job_search.services.search import pipeline
from job_search.services.search.pipeline import results_for

log = logging.getLogger(__name__)

# on_event(name, data) lets a UI follow along. Names: "stage", "profile", "site", "progress", "funnel".
EventCallback = Callable[[str, dict], None]


def run(
    options: SearchOptions,
    settings: Settings,
    on_event: EventCallback | None = None,
    stop_event: threading.Event | None = None,
) -> SearchResult:
    """Run a full search. Raises SearchStopped if stop_event gets set. Every run is saved in the run history."""
    stop_event = stop_event or threading.Event()
    stats = RunStats()
    started_at = datetime.now().isoformat(timespec="seconds")
    clock = time.monotonic()
    status, error, result = "error", None, None

    def emit(name: str, **data) -> None:
        # Keep a copy for the run history, then pass it on to the UI.
        if name == "site":
            stats.sites[data["site"]] = {"status": data["status"], "found": data["found"]}
        elif name == "funnel":
            stats.funnel = list(data["steps"])
        if on_event:
            on_event(name, data)

    try:
        result = pipeline.run_pipeline(options, settings, emit, stop_event, stats)
        status = "done"
        return result
    except SearchStopped:
        status = "stopped"
        raise
    except Exception as exc:
        error = str(exc) or exc.__class__.__name__
        raise
    finally:
        stats.duration_s = round(time.monotonic() - clock, 1)
        stats.cost_usd = stats.usage.cost_usd(settings.price_input, settings.price_output, settings.price_cached_input)
        _log_summary(status, stats)
        if options.history_path:
            _record_run(options, started_at, status, stats, result, error)


def _log_summary(status: str, stats: RunStats) -> None:
    usage = stats.usage
    cost = f" · ~${stats.cost_usd:.4f}" if stats.cost_usd is not None else ""
    log.info(
        "Run %s in %.0fs · AI: %d calls, %d tokens in (%d cached), %d out%s · reused %d scores, %d descriptions",
        status, stats.duration_s, usage.calls, usage.input_tokens, usage.cached_tokens,
        usage.output_tokens, cost, stats.scores_reused, stats.descriptions_reused,
    )


def _record_run(
    options: SearchOptions, started_at: str, status: str, stats: RunStats, result: SearchResult | None, error: str | None
) -> None:
    shown = [job for jobs in result.top_by_site.values() for job in jobs] if result else []
    data = {
        "duration_s": stats.duration_s,
        "sites": stats.sites or {site: {"status": "not run", "found": 0} for site in options.sites},
        "requested": {site: results_for(options, site) for site in options.sites},
        "keywords": options.keywords,
        "locations": options.locations,
        "experience": list(options.experience) if options.experience else None,
        "hours": options.max_age_hours,
        "funnel": stats.funnel,
        "shown": len(shown),
        "new": sum(1 for job in shown if job.is_new),
        "report": str(Path(result.html_path).resolve()) if result else None,
        "usage": asdict(stats.usage),
        "cost_usd": stats.cost_usd,
        "scores_reused": stats.scores_reused,
        "descriptions_reused": stats.descriptions_reused,
        "error": error,
    }
    try:
        JobHistoryRepository(options.history_path).record_run(started_at, options.origin, status, data)
    except Exception:  # the run history must never break a run
        log.exception("Couldn't save the run history")
