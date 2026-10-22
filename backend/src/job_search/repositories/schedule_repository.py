"""JSON-file persistence for the saved daily-search schedule and its last-run state."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from job_search.models import Schedule

SCHEDULE_FILE = "schedule.json"
STATE_FILE = "schedule_state.json"
LOG_FILE = "scheduled.log"


def save_schedule(data_dir: Path, schedule: Schedule) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    schedule.saved_at = datetime.now().isoformat(timespec="seconds")
    (data_dir / SCHEDULE_FILE).write_text(json.dumps(asdict(schedule), indent=2), encoding="utf-8")


def load_schedule(data_dir: Path) -> Schedule | None:
    path = data_dir / SCHEDULE_FILE
    if not path.exists():
        return None
    return Schedule(**json.loads(path.read_text(encoding="utf-8")))


def delete_schedule(data_dir: Path) -> None:
    (data_dir / SCHEDULE_FILE).unlink(missing_ok=True)


def save_state(data_dir: Path, **state) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / STATE_FILE).write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_state(data_dir: Path) -> dict | None:
    path = data_dir / STATE_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
