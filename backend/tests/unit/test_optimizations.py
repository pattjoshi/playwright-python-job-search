"""Tests for the speed / cost / reliability work: retries, parallel scoring, cleanup (caching: test_cache.py)."""

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from openai import BadRequestError

import job_search.api.app as app_module
import job_search.config.settings as settings_module
from job_search.config import Settings, load_settings
from job_search.models import Job, Profile, Schedule
from job_search.repositories import CacheRepository, JobHistoryRepository, save_schedule, save_state
from job_search.services.cleanup_service import cleanup
from job_search.services.llm_service import JobMatcherLLM
from job_search.services.matching_service import search_locations
from job_search.services.scraping.linkedin import LinkedInScraper
from job_search.services.scraping.naukri import NaukriScraper, search_url

SAMPLE_RESUME = Path(__file__).parent.parent / "sample_resume.txt"


def job(job_id, source="linkedin", **kwargs):
    return Job(source, job_id, f"Job {job_id}", "Co", "Pune", f"https://example.com/{job_id}", **kwargs)


# ---------- LLM: strict schema, fallback, parallel batches ----------

def reply(data):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])


def test_strict_schema_is_requested():
    client = MagicMock()
    client.chat.completions.create.return_value = reply({"skills": ["Python"]})
    JobMatcherLLM("key", "model", client=client).extract_profile("resume")

    response_format = client.chat.completions.create.call_args.kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert "years_experience" in response_format["json_schema"]["schema"]["required"]


def test_falls_back_to_json_mode_when_schema_unsupported():
    error = BadRequestError(
        "Invalid parameter: 'response_format' of type 'json_schema' is not supported with this model.",
        response=httpx.Response(400, request=httpx.Request("POST", "https://api.openai.com")),
        body=None,
    )
    client = MagicMock()
    client.chat.completions.create.side_effect = [error, reply({"skills": ["Go"]}), reply({"skills": ["Rust"]})]
    llm = JobMatcherLLM("key", "model", client=client)

    assert llm.extract_profile("resume").skills == ["Go"]
    assert llm.extract_profile("resume").skills == ["Rust"]  # remembers: no second failed attempt
    formats = [c.kwargs["response_format"]["type"] for c in client.chat.completions.create.call_args_list]
    assert formats == ["json_schema", "json_object", "json_object"]


def test_scoring_runs_batches_in_parallel():
    in_flight, peak, lock = 0, 0, threading.Lock()

    def create(**kwargs):
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.05)
        jobs = json.loads(kwargs["messages"][1]["content"].split("JOBS:\n", 1)[1])
        with lock:
            in_flight -= 1
        return reply({"results": [{"id": j["id"], "score": 70, "reason": "ok", "matched_skills": [], "missing_skills": []} for j in jobs]})

    client = MagicMock()
    client.chat.completions.create.side_effect = create
    jobs = [job(str(i)) for i in range(40)]
    seen = []

    JobMatcherLLM("key", "model", client=client, concurrency=4).score_jobs(Profile(), jobs, progress=lambda d, t: seen.append(d))

    assert all(j.score == 70 for j in jobs)
    assert peak > 1
    assert seen[0] == 0 and seen[-1] == 40


def test_stop_during_scoring_cancels_remaining_batches():
    from job_search.services.matching_service import SearchStopped

    client = MagicMock()
    client.chat.completions.create.side_effect = lambda **kw: (time.sleep(0.02), reply({"results": []}))[1]
    calls = []

    def progress(done, total):
        calls.append(done)
        if done:
            raise SearchStopped()

    with pytest.raises(SearchStopped):
        llm = JobMatcherLLM("key", "model", client=client, concurrency=1)
        llm.score_jobs(Profile(), [job(str(i)) for i in range(50)], progress=progress)
    assert client.chat.completions.create.call_count < 5


def test_openai_client_retries():
    llm = JobMatcherLLM("sk-test", "model")
    assert llm.client.max_retries >= 3


# ---------- Naukri combined cities (pure URL building) ----------

def test_naukri_combines_cities():
    assert search_url("SDET", "Pune, Bengaluru", 1, 1) == (
        "https://www.naukri.com/sdet-jobs-in-pune-bengaluru?k=SDET&jobAge=1&l=Pune%2C+Bengaluru"
    )
    naukri = NaukriScraper(context=None)
    assert search_locations(naukri, ["Pune", "Remote", "Bengaluru"]) == ["Pune, Bengaluru", "Remote"]
    # A long city list goes in groups of three: one long list finds fewer jobs than the cities alone.
    cities = ["Hyderabad", "Remote", "Chennai", "Pune", "Delhi", "Mumbai", "Bengaluru", "Kochi"]
    assert search_locations(naukri, cities) == [
        "Hyderabad, Chennai, Pune", "Delhi, Mumbai, Bengaluru", "Kochi", "Remote",
    ]
    assert search_locations(naukri, ["Remote"]) == ["Remote"]
    linkedin = LinkedInScraper(context=None)
    assert search_locations(linkedin, ["Pune", "Remote"]) == ["Pune", "Remote"]


# ---------- cleanup ----------

def _old(path: Path, days: int) -> Path:
    import os

    stamp = time.time() - days * 86_400
    os.utime(path, (stamp, stamp))
    return path


def _file(path: Path, days_old: int | None = None) -> Path:
    path.write_text("x")
    return _old(path, days_old) if days_old else path


def test_cleanup_removes_old_files_but_protects_important_ones(tmp_path):
    data, uploads, output = tmp_path / "data", tmp_path / "uploads", tmp_path / "output"
    for folder in (data, uploads, output):
        folder.mkdir()
    old_resume = _file(uploads / "old.pdf", 40)
    new_resume = _file(uploads / "new.pdf")
    daily_resume = _file(uploads / "daily.pdf", 90)
    old_report = _file(output / "jobs_old.html", 40)
    last_report = _file(output / "jobs_last.html", 40)
    last_excel = _file(output / "jobs_last.xlsx", 40)
    keep_note = _file(output / "notes.txt", 40)
    save_schedule(data, Schedule("09:00", search={"resume_path": str(daily_resume)}))
    save_state(data, last_run="2026-10-01T09:00:00", status="done", report=str(last_report))
    history = JobHistoryRepository(data / "history.sqlite3")
    history.set_status("linkedin", "1", "applied")
    cache = CacheRepository(data / "cache.sqlite3")
    cache.save_descriptions([job("1", description="x")])
    with cache._db.connect() as db:
        db.execute("UPDATE job_details SET saved_at = '2000-01-01T00:00:00'")

    result = cleanup(30, data, uploads, output, data / "cache.sqlite3")

    assert not old_resume.exists() and not old_report.exists()
    assert new_resume.exists() and daily_resume.exists()
    assert last_report.exists() and last_excel.exists() and keep_note.exists()
    assert (result.files, result.cache_rows) == (2, 1)
    assert history.counts()["applied"] == 1  # history is never touched


def test_cleanup_disabled_and_log_trim(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    old = _file(uploads / "old.pdf", 400)
    assert cleanup(0, tmp_path, uploads, tmp_path / "output").files == 0
    assert old.exists()

    log = tmp_path / "scheduled.log"
    log.write_bytes(b"old line\n" * 400_000)  # ~3.6 MB
    assert cleanup(30, tmp_path, uploads, tmp_path / "output").log_trimmed
    assert log.stat().st_size <= 512 * 1024
    assert log.read_bytes().startswith(b"old line")


def test_keep_days_setting(monkeypatch):
    monkeypatch.setattr(settings_module, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("KEEP_DAYS", "0")
    assert load_settings().keep_days == 0
    monkeypatch.setenv("KEEP_DAYS", "-1")
    with pytest.raises(ValueError, match="KEEP_DAYS"):
        load_settings()
    monkeypatch.delenv("KEEP_DAYS")
    settings = load_settings()
    assert settings.keep_days == 30
    assert settings.cache_path == settings.history_path.parent / "cache.sqlite3"


# ---------- resume reading is cached in the web app ----------

def test_web_analyzer_reads_same_resume_once(tmp_path, monkeypatch):
    calls = []

    class FakeLLM:
        def __init__(self, *args):
            pass

        def extract_profile(self, text):
            calls.append(text)
            return Profile(skills=["Python"])

    monkeypatch.setattr(app_module, "JobMatcherLLM", FakeLLM)
    analyze = app_module.default_analyzer(Settings("key", history_path=tmp_path / "history.sqlite3"))
    first = tmp_path / "cv.txt"
    first.write_text("Python developer")
    copy = tmp_path / "cv (1).txt"
    copy.write_text("Python developer")

    assert analyze(first).skills == ["Python"]
    assert analyze(copy).skills == ["Python"]
    assert len(calls) == 1
