import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import job_search.daily as daily
from job_search.models import Job, Profile
from job_search.pipeline import SearchOptions, SearchResult
from job_search.schedule import (
    CRON_MARKER,
    Schedule,
    ScheduleError,
    SystemScheduler,
    clean_days,
    load_schedule,
    load_state,
    options_from_dict,
    options_to_dict,
    parse_time,
    save_schedule,
)


def test_parse_time_and_days():
    assert parse_time("09:00") == (9, 0)
    assert parse_time(" 18:45 ") == (18, 45)
    for bad in ("9am", "24:00", "12:60", ""):
        with pytest.raises(ValueError):
            parse_time(bad)
    assert clean_days(["Fri", "mon", "monday"]) == ["mon", "fri"]
    with pytest.raises(ValueError, match="at least one day"):
        clean_days([])
    with pytest.raises(ValueError, match="Unknown day"):
        clean_days(["someday"])


def test_next_run():
    thursday_8am = datetime(2026, 10, 1, 8, 0)  # a Thursday
    assert Schedule("09:00").next_run(thursday_8am) == datetime(2026, 10, 1, 9, 0)
    assert Schedule("07:30").next_run(thursday_8am) == datetime(2026, 10, 2, 7, 30)
    weekdays = Schedule("09:00", days=["mon", "tue", "wed", "thu", "fri"])
    friday_10am = datetime(2026, 10, 2, 10, 0)
    assert weekdays.next_run(friday_10am) == datetime(2026, 10, 5, 9, 0)  # skips the weekend


def test_options_round_trip(tmp_path):
    options = SearchOptions(
        resume_path=tmp_path / "cv.pdf",
        sites=["naukri"],
        locations=["Pune", "Remote"],
        keywords=["SDET"],
        experience=(1, 3),
        results_per_site={"naukri": 12},
        profile=Profile(skills=["Python"], years_experience=3),
        output_dir=tmp_path / "out",
        history_path=tmp_path / "h.sqlite3",
    )
    data = json.loads(json.dumps(options_to_dict(options)))  # must survive JSON
    restored = options_from_dict(data)

    assert restored.resume_path == (tmp_path / "cv.pdf").resolve()
    assert restored.experience == (1, 3)
    assert restored.profile == options.profile
    assert (restored.sites, restored.locations, restored.results_per_site) == (["naukri"], ["Pune", "Remote"], {"naukri": 12})


def test_save_and_load_schedule(tmp_path):
    save_schedule(tmp_path, Schedule("09:00", ["mon"], False, {"keywords": ["SDET"]}))
    loaded = load_schedule(tmp_path)
    assert (loaded.time, loaded.days, loaded.open_report, loaded.search) == ("09:00", ["mon"], False, {"keywords": ["SDET"]})
    assert loaded.saved_at


class FakeRun:
    def __init__(self, crontab="", fail=False):
        self.calls = []
        self.crontab = crontab
        self.fail = fail

    def __call__(self, command, capture_output=True, text=True, input=None):
        self.calls.append((command, input))
        if command == ["crontab", "-l"]:
            return SimpleNamespace(returncode=0, stdout=self.crontab, stderr="")
        if command == ["crontab", "-"]:
            self.crontab = input
        return SimpleNamespace(returncode=1 if self.fail else 0, stdout="", stderr="Access is denied." if self.fail else "")


def test_windows_task(tmp_path):
    runner = FakeRun()
    scheduler = SystemScheduler(tmp_path, workdir=Path("C:/jobs"), python="C:/jobs/.venv/Scripts/python.exe", platform="win32", runner=runner)

    scheduler.install(Schedule("09:15", days=["mon", "wed"]))

    command, _ = runner.calls[0]
    assert command[:4] == ["schtasks", "/Create", "/TN", "JobSearchDaily"] and command[-1] == "/F"
    xml = (tmp_path / "daily_task.xml").read_text(encoding="utf-16")
    assert "T09:15:00</StartBoundary>" in xml
    assert "<Monday /><Wednesday />" in xml
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in xml
    assert "<Arguments>-m job_search.daily</Arguments>" in xml
    assert "python.exe</Command>" in xml

    scheduler.remove()
    assert runner.calls[-1][0] == ["schtasks", "/Delete", "/TN", "JobSearchDaily", "/F"]


def test_windows_error_is_reported(tmp_path):
    scheduler = SystemScheduler(tmp_path, platform="win32", runner=FakeRun(fail=True))
    with pytest.raises(ScheduleError, match="Access is denied"):
        scheduler.install(Schedule("09:00"))


def test_cron_install_replaces_only_our_line(tmp_path):
    runner = FakeRun(crontab="0 1 * * * backup.sh\n5 8 * * * old job_search " + CRON_MARKER + "\n")
    scheduler = SystemScheduler(tmp_path, workdir=Path("/home/me/jobs"), python="/usr/bin/python3", platform="linux", runner=runner)

    scheduler.install(Schedule("09:05", days=["mon", "tue", "wed", "thu", "fri"]))

    lines = runner.crontab.splitlines()
    assert lines[0] == "0 1 * * * backup.sh"
    assert len(lines) == 2
    assert lines[1].startswith("5 9 * * 1,2,3,4,5 cd /home/me/jobs && /usr/bin/python3 -m job_search.daily >> ")
    assert lines[1].endswith(CRON_MARKER)
    assert scheduler.cron_line(Schedule("07:00")).startswith("0 7 * * * ")

    scheduler.remove()
    assert runner.crontab == "0 1 * * * backup.sh\n"


def test_daily_runner_saves_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HISTORY_DB", str(tmp_path / "data" / "history.sqlite3"))
    options = SearchOptions(resume_path=tmp_path / "cv.txt", sites=["naukri"], output_dir=tmp_path / "out")
    save_schedule(tmp_path / "data", Schedule("09:00", open_report=False, search=options_to_dict(options)))
    report = tmp_path / "out" / "r.html"

    def fake_run(opts, settings):
        assert opts.sites == ["naukri"]
        jobs = [Job("naukri", "1", "SDET", "Co", "Pune", "u", is_new=True), Job("naukri", "2", "QA", "Co", "Pune", "u", is_new=False)]
        return SearchResult(Profile(), jobs, {"naukri": jobs}, report, report, report)

    monkeypatch.setattr(daily, "run", fake_run)
    opened = []
    monkeypatch.setattr(daily.webbrowser, "open", opened.append)

    assert daily.main() == 0
    state = load_state(tmp_path / "data")
    assert (state["status"], state["jobs"], state["new"]) == ("done", 2, 1)
    assert opened == []  # open_report=False


def test_daily_runner_records_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HISTORY_DB", str(tmp_path / "data" / "history.sqlite3"))
    options = SearchOptions(resume_path=tmp_path / "missing.pdf")
    save_schedule(tmp_path / "data", Schedule("09:00", search=options_to_dict(options)))

    def broken(opts, settings):
        raise FileNotFoundError("Resume not found: missing.pdf")

    monkeypatch.setattr(daily, "run", broken)
    assert daily.main() == 1
    assert load_state(tmp_path / "data")["error"] == "Resume not found: missing.pdf"


def test_daily_runner_without_schedule(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HISTORY_DB", str(tmp_path / "data" / "history.sqlite3"))
    assert daily.main() == 1
