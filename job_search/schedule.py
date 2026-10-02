"""Daily search: save the search settings and register an OS task that runs them.

Windows uses Task Scheduler (the task runs even when the web UI is closed and,
if the laptop was off or asleep at that time, as soon as it's back on).
macOS/Linux use cron. The task runs `python -m job_search.daily`.
"""

import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from job_search.models import Profile
from job_search.pipeline import SearchOptions

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TASK_NAME = "JobSearchDaily"
CRON_MARKER = "# job-search-daily"
SCHEDULE_FILE = "schedule.json"
STATE_FILE = "schedule_state.json"
LOG_FILE = "scheduled.log"


class ScheduleError(Exception):
    """The OS scheduler refused the task (message is shown to the user)."""


@dataclass
class Schedule:
    time: str  # "HH:MM", 24-hour, local time
    days: list[str] = field(default_factory=lambda: list(DAYS))
    open_report: bool = True
    search: dict = field(default_factory=dict)  # serialized SearchOptions
    saved_at: str = ""

    def next_run(self, now: datetime | None = None) -> datetime:
        now = now or datetime.now()
        hour, minute = parse_time(self.time)
        for offset in range(8):
            day = now + timedelta(days=offset)
            candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if DAYS[candidate.weekday()] in self.days and candidate > now:
                return candidate
        raise ValueError("schedule has no days")  # can't happen after validation


def parse_time(text: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = text.strip().split(":")
        hour, minute = int(hour_text), int(minute_text)
    except (AttributeError, ValueError):
        raise ValueError("Time must look like 09:00") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Time must be between 00:00 and 23:59")
    return hour, minute


def clean_days(days) -> list[str]:
    if not isinstance(days, list) or not days:
        raise ValueError("Pick at least one day")
    picked = {str(day).lower()[:3] for day in days}
    unknown = picked - set(DAYS)
    if unknown:
        raise ValueError(f"Unknown day(s): {', '.join(sorted(unknown))}")
    return [day for day in DAYS if day in picked]


# ---------- saving the search settings ----------

def options_to_dict(options: SearchOptions) -> dict:
    data = {}
    for f in fields(SearchOptions):
        value = getattr(options, f.name)
        if isinstance(value, Path):
            value = str(value.resolve())
        elif isinstance(value, Profile):
            value = asdict(value)
        elif isinstance(value, tuple):
            value = list(value)
        data[f.name] = value
    return data


def options_from_dict(data: dict) -> SearchOptions:
    known = {f.name for f in fields(SearchOptions)}
    values = {key: value for key, value in data.items() if key in known}
    for key in ("resume_path", "output_dir", "history_path", "cache_path"):
        if values.get(key):
            values[key] = Path(values[key])
    if values.get("experience"):
        values["experience"] = tuple(values["experience"])
    if isinstance(values.get("profile"), dict):
        values["profile"] = Profile(**values["profile"])
    return SearchOptions(**values)


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


# ---------- registering the OS task ----------

class SystemScheduler:
    """Installs/removes the daily task. `runner` is subprocess.run (swappable in tests)."""

    def __init__(self, data_dir: Path, workdir: Path | None = None, python: str | None = None,
                 platform: str | None = None, runner=subprocess.run):
        self.data_dir = data_dir.resolve()
        self.workdir = (workdir or Path.cwd()).resolve()
        self.python = python or sys.executable
        self.platform = platform or sys.platform
        self.runner = runner

    @property
    def kind(self) -> str:
        if self.platform.startswith("win"):
            return "windows"
        if self.platform.startswith(("linux", "darwin")):
            return "cron"
        return "unsupported"

    def install(self, schedule: Schedule) -> None:
        if self.kind == "windows":
            xml_path = self.data_dir / "daily_task.xml"
            self.data_dir.mkdir(parents=True, exist_ok=True)
            # Task Scheduler expects UTF-16 for XML task definitions.
            xml_path.write_text(self.task_xml(schedule), encoding="utf-16")
            self._run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"])
        elif self.kind == "cron":
            lines = [line for line in self._crontab() if CRON_MARKER not in line]
            lines.append(self.cron_line(schedule))
            self._run(["crontab", "-"], input="\n".join(lines) + "\n")
        else:
            raise ScheduleError(f"Daily search isn't supported on {self.platform}.")

    def remove(self) -> None:
        if self.kind == "windows":
            self._run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], allow_fail=True)
        elif self.kind == "cron":
            lines = [line for line in self._crontab() if CRON_MARKER not in line]
            self._run(["crontab", "-"], input="\n".join(lines) + ("\n" if lines else ""))

    def task_xml(self, schedule: Schedule) -> str:
        hour, minute = parse_time(schedule.time)
        start = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        day_tags = "".join(f"<{_FULL_DAY[day]} />" for day in schedule.days)
        return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Daily job search (created by the Job Search app)</Description></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start:%Y-%m-%dT%H:%M:%S}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek><DaysOfWeek>{day_tags}</DaysOfWeek><WeeksInterval>1</WeeksInterval></ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(self.python)}</Command>
      <Arguments>-m job_search.daily</Arguments>
      <WorkingDirectory>{escape(str(self.workdir))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

    def cron_line(self, schedule: Schedule) -> str:
        hour, minute = parse_time(schedule.time)
        # cron weekdays: 0 = Sunday ... 6 = Saturday
        weekdays = "*" if len(schedule.days) == 7 else ",".join(str((DAYS.index(d) + 1) % 7) for d in schedule.days)
        log = self.data_dir / LOG_FILE
        command = (
            f"cd {shlex.quote(str(self.workdir))} && "
            f"{shlex.quote(self.python)} -m job_search.daily >> {shlex.quote(str(log))} 2>&1"
        )
        return f"{minute} {hour} * * {weekdays} {command} {CRON_MARKER}"

    def _crontab(self) -> list[str]:
        result = self.runner(["crontab", "-l"], capture_output=True, text=True)
        return result.stdout.splitlines() if result.returncode == 0 else []

    def _run(self, command: list[str], input: str | None = None, allow_fail: bool = False) -> None:
        try:
            result = self.runner(command, capture_output=True, text=True, input=input)
        except FileNotFoundError:
            raise ScheduleError(f"Couldn't find '{command[0]}' on this computer.") from None
        if result.returncode != 0 and not allow_fail:
            message = (result.stderr or result.stdout or "").strip() or f"{command[0]} failed"
            raise ScheduleError(message)


_FULL_DAY = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}
