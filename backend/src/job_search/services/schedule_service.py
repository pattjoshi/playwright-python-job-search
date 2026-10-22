"""Daily search: turn saved settings into an OS task that runs them.

Windows uses Task Scheduler (the task runs even when the web UI is closed and,
if the laptop was off or asleep at that time, as soon as it's back on).
macOS/Linux use cron. The task runs `python -m job_search.daily`.
"""

import shlex
import subprocess
import sys
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from job_search.models import DAYS, Profile, Schedule, SearchOptions, parse_time

TASK_NAME = "JobSearchDaily"
CRON_MARKER = "# job-search-daily"


class ScheduleError(Exception):
    """The OS scheduler refused the task (message is shown to the user)."""


def clean_days(days) -> list[str]:
    if not isinstance(days, list) or not days:
        raise ValueError("Pick at least one day")
    picked = {str(day).lower()[:3] for day in days}
    unknown = picked - set(DAYS)
    if unknown:
        raise ValueError(f"Unknown day(s): {', '.join(sorted(unknown))}")
    return [day for day in DAYS if day in picked]


# ---------- converting SearchOptions to/from a JSON-friendly dict ----------

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
        log = self.data_dir / "scheduled.log"
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
