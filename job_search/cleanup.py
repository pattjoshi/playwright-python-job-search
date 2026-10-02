"""Deletes old files so personal data doesn't pile up (KEEP_DAYS, default 30; 0 = keep forever).

Removed after KEEP_DAYS:  uploaded resumes, reports (HTML/Excel/CSV), cached descriptions/scores.
Never removed:            job history (seen/applied/hidden), the resume used by the daily search,
                          the report of the last daily run. The daily-run log is trimmed, not deleted.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from job_search.cache import Cache
from job_search.schedule import LOG_FILE, load_schedule, load_state

log = logging.getLogger(__name__)

REPORT_SUFFIXES = {".html", ".xlsx", ".csv"}
MAX_LOG_BYTES = 2 * 1024 * 1024
KEEP_LOG_BYTES = 512 * 1024


@dataclass
class CleanupResult:
    files: int = 0
    cache_rows: int = 0
    log_trimmed: bool = False


def cleanup(
    keep_days: int,
    data_dir: Path,
    upload_dir: Path = Path("uploads"),
    output_dir: Path = Path("output"),
    cache_path: Path | None = None,
    now: float | None = None,
) -> CleanupResult:
    result = CleanupResult()
    if keep_days <= 0:
        return result
    cutoff = (now or time.time()) - keep_days * 86_400
    protected = _protected_files(data_dir)

    for folder, suffixes in ((upload_dir, None), (output_dir, REPORT_SUFFIXES)):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file() or (suffixes and path.suffix.lower() not in suffixes):
                continue
            if path.resolve() in protected or path.stat().st_mtime >= cutoff:
                continue
            try:
                path.unlink()
                result.files += 1
            except OSError as error:  # e.g. the report is open in Excel on Windows
                log.debug("Couldn't delete %s: %s", path, error)

    if cache_path and Path(cache_path).exists():
        result.cache_rows = Cache(cache_path).delete_older_than(keep_days)

    result.log_trimmed = _trim_log(data_dir / LOG_FILE)
    if result.files or result.cache_rows or result.log_trimmed:
        log.info(
            "Cleanup: removed %d old files and %d cached entries older than %d days%s",
            result.files, result.cache_rows, keep_days, "; trimmed the daily-run log" if result.log_trimmed else "",
        )
    return result


def _protected_files(data_dir: Path) -> set[Path]:
    protected: set[Path] = set()
    schedule = load_schedule(data_dir)
    if schedule and schedule.search.get("resume_path"):
        protected.add(Path(schedule.search["resume_path"]).resolve())
    state = load_state(data_dir)
    if state and state.get("report"):
        report = Path(state["report"]).resolve()
        protected |= {report, report.with_suffix(".xlsx"), report.with_suffix(".csv")}
    return protected


def _trim_log(path: Path) -> bool:
    """Keep only the newest part of a log that has grown too big."""
    if not path.exists() or path.stat().st_size <= MAX_LOG_BYTES:
        return False
    data = path.read_bytes()[-KEEP_LOG_BYTES:]
    newline = data.find(b"\n")
    path.write_bytes(data[newline + 1 :] if newline != -1 else data)
    return True
