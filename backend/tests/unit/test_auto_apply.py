"""Auto-apply rules without a browser: platforms, settings, the queue, and the background runner."""

import threading

import pytest

from job_search.models import Job
from job_search.repositories import UserRepository
from job_search.services.auto_apply import AutoApplyError, AutoApplyManager, clean_settings
from job_search.services.auto_apply.platforms import detect, form_url
from tests.auto_apply_support import make_service


def job(job_id, score=90, apply_url="https://jobs.lever.co/acme/abc"):
    return Job("naukri", job_id, "SDET", "Acme", "Pune", f"https://naukri.com/{job_id}", score=score, apply_url=apply_url)


def test_platforms():
    assert detect("https://boards.greenhouse.io/acme/jobs/1") == "greenhouse"
    assert detect("https://acme.com/careers?gh_jid=123") == "greenhouse"
    assert detect("https://jobs.lever.co/acme/abc") == "lever" and detect("https://jobs.ashbyhq.com/acme/x") == "ashby"
    assert detect("https://acme.wd5.myworkdayjobs.com/x") == "workday" and detect("https://acme.com/jobs/1") == "other"
    assert form_url("https://jobs.lever.co/acme/abc?src=li", "lever") == "https://jobs.lever.co/acme/abc/apply"
    assert form_url("https://jobs.lever.co/acme/abc/apply", "lever") == "https://jobs.lever.co/acme/abc/apply"
    assert form_url("https://jobs.ashbyhq.com/acme/x", "ashby") == "https://jobs.ashbyhq.com/acme/x/application"
    assert form_url("https://acme.com/jobs/1", "other") == "https://acme.com/jobs/1"


def test_settings_validation():
    assert clean_settings({"dry_run": False, "min_score": 60, "other": 1}) == {"dry_run": False, "min_score": 60}
    for bad in ({"min_score": 101}, {"daily_limit": 0}, {"daily_limit": "5"}, {"min_score": True}, {"dry_run": "no"}):
        with pytest.raises(AutoApplyError):
            clean_settings(bad)


def test_queue_rules_retry_and_remove(tmp_path):
    service = make_service(tmp_path)
    overview = service.overview(1)
    assert overview["settings"]["dry_run"] is True and overview["remaining"] == 15  # safe defaults

    service.save_settings(1, {"min_score": 80})
    assert service.queue_jobs(1, [job("1"), job("2", score=79), job("3", apply_url=""), job("4", score=None)]) == 1
    assert service.queue_jobs(1, [job("1")]) == 0  # same company link: queued once
    queued = service.repo.for_user(1)[0]
    assert (queued["platform"], queued["status"], queued["score"]) == ("lever", "queued", 90)

    service.repo.update(1, queued["id"], {"status": "failed", "message": "boom"})
    assert service.retry(1, queued["id"])["status"] == "queued"
    service.remove(1, queued["id"])
    assert service.repo.for_user(1) == []
    with pytest.raises(AutoApplyError) as missing:
        service.retry(1, queued["id"])
    assert missing.value.status == 404


def test_run_needs_a_resume(tmp_path):
    service = make_service(tmp_path, resume=False)
    service.queue_jobs(1, [job("1")])
    with pytest.raises(AutoApplyError, match="Upload your resume"):
        service.run(1, threading.Event())


def test_manager_queues_after_search_and_reports_errors(tmp_path):
    service = make_service(tmp_path, resume=False)
    manager = AutoApplyManager(service, start_thread=lambda target: target())  # run in the test's thread
    assert manager.after_search(1, [job("1")]) == 1 and manager.state["status"] == "idle"  # not asked to run

    service.save_settings(1, {"run_after_search": True})
    manager.after_search(1, [job("2", apply_url="https://jobs.lever.co/acme/def")])
    assert manager.state["status"] == "error" and "Upload your resume" in manager.state["error"]
    assert manager.after_search(999, [job("3")]) == 0  # a broken queue never breaks the search
    assert UserRepository(tmp_path / "h.sqlite3").owner_id() == 1


def test_manager_runs_one_at_a_time_and_stops(tmp_path):
    service = make_service(tmp_path)
    pending = []
    manager = AutoApplyManager(service, start_thread=pending.append)
    assert manager.start(1)["status"] == "running"
    with pytest.raises(AutoApplyError, match="is running"):
        manager.start(1)
    assert manager.stop()["status"] == "stopping"
    pending[0]()  # the run sees Stop straight away
    assert manager.state["status"] == "stopped" and manager.state["logs"][-1].endswith("Stopped.")


def test_daily_search_queues_matches(tmp_path):
    from job_search.cli.daily import auto_apply_matches
    from job_search.config import Settings

    service = make_service(tmp_path)  # creates the owner account
    auto_apply_matches(Settings(openai_api_key="", history_path=tmp_path / "h.sqlite3"), [job("1"), job("2", score=10)])
    assert [j["source_job_id"] for j in service.repo.for_user(1)] == ["1"]  # run_after_search is off: queued only


def test_board_limits_and_logins(monkeypatch):
    from job_search.config.settings import load_settings
    from job_search.services.auto_apply.service import remaining_today

    settings = {"daily_limit": 15, "board_daily_limit": 10}
    left = remaining_today(settings, {"lever": 3, "other": 2, "naukri": 10, "linkedin": 4})
    assert left == {"company": 10, "naukri": 0, "linkedin": 6, "indeed": 10}
    with pytest.raises(AutoApplyError):
        clean_settings({"board_daily_limit": 51})
    assert clean_settings({"naukri": True, "board_daily_limit": 5}) == {"naukri": True, "board_daily_limit": 5}

    monkeypatch.setenv("NAUKRI_EMAIL", "om@example.com")
    monkeypatch.setenv("NAUKRI_PASSWORD", "s3cret-pass")
    monkeypatch.setenv("LINKEDIN_EMAIL", "om@example.com")  # no password: LinkedIn isn't set up
    monkeypatch.delenv("LINKEDIN_PASSWORD", raising=False)
    loaded = load_settings()
    assert loaded.board_logins.get("naukri") == ("om@example.com", "s3cret-pass") and "linkedin" not in loaded.board_logins
    assert "s3cret-pass" not in repr(loaded)  # never printed in logs or errors
