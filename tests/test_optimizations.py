"""Tests for the speed / cost / reliability work: caching, retries, parallel scoring, cleanup."""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from openai import BadRequestError

import job_search.config as config
import job_search.pipeline as pipeline
import job_search.web as web
from job_search.cache import Cache, profile_key, resume_key
from job_search.cleanup import cleanup
from job_search.config import Settings, load_settings
from job_search.history import JobHistory
from job_search.llm import JobMatcherLLM
from job_search.models import Job, Profile
from job_search.pipeline import SearchOptions, block_assets, run, search_locations
from job_search.schedule import Schedule, save_schedule, save_state
from job_search.scrapers.linkedin import LinkedInScraper
from job_search.scrapers.naukri import NaukriScraper, search_url
from job_search.utils import SearchStopped

SAMPLE_RESUME = Path(__file__).parent / "sample_resume.txt"


def job(job_id, source="linkedin", **kwargs):
    return Job(source, job_id, f"Job {job_id}", "Co", "Pune", f"https://example.com/{job_id}", **kwargs)


# ---------- cache ----------

def test_cache_descriptions_scores_profiles(tmp_path):
    cache = Cache(tmp_path / "cache.sqlite3")
    cache.save_descriptions([job("1", description="Python role", experience="2-4 Yrs"), job("2")])  # empty not saved

    jobs = [job("1"), job("2")]
    assert [j.job_id for j in cache.fill_descriptions(jobs)] == ["2"]
    assert (jobs[0].description, jobs[0].experience) == ("Python role", "2-4 Yrs")

    scored = job("1", score=88, match_reason="fit", matched_skills=["Python"], missing_skills=["Go"])
    cache.save_scores([scored, job("2")], "key-a")  # unscored job isn't cached
    fresh = [job("1"), job("2")]
    assert [j.job_id for j in cache.fill_scores(fresh, "key-a")] == ["2"]
    assert (fresh[0].score, fresh[0].match_reason, fresh[0].matched_skills, fresh[0].missing_skills) == (88, "fit", ["Python"], ["Go"])
    assert len(cache.fill_scores([job("1")], "key-b")) == 1  # other profile -> not reused

    cache.save_profile("r1", Profile(skills=["Python"], years_experience=3))
    assert cache.get_profile("r1") == Profile(skills=["Python"], years_experience=3)
    assert cache.get_profile("nope") is None


def test_cache_keys(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "renamed.txt"
    a.write_text("same resume")
    b.write_text("same resume")
    assert resume_key(a, "m") == resume_key(b, "m") != resume_key(a, "other-model")

    base = profile_key(Profile(skills=["Python"]), (1, 2), "m", "prompt")
    assert base == profile_key(Profile(skills=["Python"]), (1, 2), "m", "prompt")
    assert base != profile_key(Profile(skills=["Python", "Go"]), (1, 2), "m", "prompt")
    assert base != profile_key(Profile(skills=["Python"]), (1, 3), "m", "prompt")
    assert base != profile_key(Profile(skills=["Python"]), (1, 2), "m", "prompt v2")


def test_cache_delete_older_than(tmp_path):
    cache = Cache(tmp_path / "c.sqlite3")
    cache.save_descriptions([job("old", description="x"), job("new", description="y")])
    with cache._connect() as db:
        db.execute("UPDATE descriptions SET saved_at = '2000-01-01T00:00:00' WHERE job_id = 'old'")
    assert cache.delete_older_than(30) == 1
    assert [j.job_id for j in cache.fill_descriptions([job("old"), job("new")])] == ["old"]


# ---------- pipeline reuses cached work ----------

class CountingScraper(pipeline.BaseScraper):
    name = "linkedin"
    fetched: list = []

    def search(self, query, location):
        return [job(str(i), posted_text="1 hour ago", hours_ago=1) for i in range(6)]

    def fetch_description(self, j):
        CountingScraper.fetched.append(j.job_id)
        j.description = "Python and Playwright"

    def pause(self):
        pass


class CountingLLM:
    extracted = 0
    scored: list = []

    def __init__(self, *args):
        pass

    def extract_profile(self, text):
        CountingLLM.extracted += 1
        return Profile(skills=["Python"], search_queries=["Python Engineer"], locations=["Pune"])

    def score_jobs(self, profile, jobs, experience=None, progress=None):
        CountingLLM.scored.append([j.job_id for j in jobs])
        for j in jobs:
            j.score = 50 + int(j.job_id)


def run_in_thread(*args, **kwargs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run, *args, **kwargs).result()


def test_second_run_reuses_descriptions_scores_and_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SCRAPERS", {"linkedin": CountingScraper})
    monkeypatch.setattr(pipeline, "JobMatcherLLM", CountingLLM)
    CountingScraper.fetched, CountingLLM.scored, CountingLLM.extracted = [], [], 0
    settings = Settings("key", "model", os.getenv("CHROMIUM_EXECUTABLE") or None)
    options = SearchOptions(SAMPLE_RESUME, sites=["linkedin"], top_n=6, cache_path=tmp_path / "cache.sqlite3", output_dir=tmp_path)

    first = run_in_thread(options, settings)
    second = run_in_thread(options, settings)

    assert sorted(CountingScraper.fetched) == [str(i) for i in range(6)]  # opened once, not twice
    assert CountingLLM.scored == [[str(i) for i in range(6)], []]  # second run scored nothing new
    assert CountingLLM.extracted == 1  # resume read once
    assert [j.score for j in second.jobs] == [j.score for j in first.jobs]
    assert second.jobs[0].description == "Python and Playwright"


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
    client = MagicMock()
    client.chat.completions.create.side_effect = lambda **kw: (time.sleep(0.02), reply({"results": []}))[1]
    calls = []

    def progress(done, total):
        calls.append(done)
        if done:
            raise SearchStopped()

    with pytest.raises(SearchStopped):
        JobMatcherLLM("key", "model", client=client, concurrency=1).score_jobs(Profile(), [job(str(i)) for i in range(50)], progress=progress)
    assert client.chat.completions.create.call_count < 5


def test_openai_client_retries():
    llm = JobMatcherLLM("sk-test", "model")
    assert llm.client.max_retries >= 3


# ---------- scrapers: retry on 429, Naukri combined cities ----------

def test_linkedin_retries_after_429(browser, fixture_html):
    context = browser.new_context()
    html = fixture_html("linkedin_search.html")
    calls = []

    def handle(route):
        calls.append(1)
        if len(calls) == 1:
            route.fulfill(status=429, body="slow down", content_type="text/plain")
        else:
            route.fulfill(body=html, content_type="text/html")

    context.route("**/seeMoreJobPostings/search*", handle)
    jobs = LinkedInScraper(context, delay_range=(0, 0)).search("Python", "India")

    assert len(calls) == 2
    assert len(jobs) == 2
    context.close()


def test_retry_wait_respects_stop(browser):
    context = browser.new_context()
    context.route("**/seeMoreJobPostings/search*", lambda route: route.fulfill(status=429, body="x"))
    stop = threading.Event()
    scraper = LinkedInScraper(context, delay_range=(0, 0), stop_event=stop)
    scraper.retry_delays = (30.0,)
    threading.Timer(0.3, stop.set).start()

    started = time.time()
    with pytest.raises(SearchStopped):
        scraper.search("Python", "India")
    assert time.time() - started < 10
    context.close()


def test_naukri_combines_cities():
    assert search_url("SDET", "Pune, Bengaluru", 1, 1) == (
        "https://www.naukri.com/sdet-jobs-in-pune-bengaluru?k=SDET&jobAge=1&l=Pune%2C+Bengaluru"
    )
    naukri = NaukriScraper(context=None)
    assert search_locations(naukri, ["Pune", "Remote", "Bengaluru"]) == ["Pune, Bengaluru", "Remote"]
    assert search_locations(naukri, ["Remote"]) == ["Remote"]
    linkedin = LinkedInScraper(context=None)
    assert search_locations(linkedin, ["Pune", "Remote"]) == ["Pune", "Remote"]


# ---------- asset blocking ----------

def test_block_assets(browser):
    page_html = (
        "<html><head><link rel='stylesheet' href='https://assets.test/site.css'></head>"
        "<body><img src='https://assets.test/logo.png'><script src='https://assets.test/app.js'></script></body></html>"
    )

    def requests_made(block_styles):
        context = browser.new_context()
        fulfilled = []

        def serve(route):
            fulfilled.append(route.request.url.rsplit("/", 1)[-1])
            route.fulfill(body=page_html if route.request.url.endswith("/") else "", content_type="text/html")

        context.route("https://assets.test/**", serve)
        block_assets(context, block_styles=block_styles)  # registered last = checked first
        page = context.new_page()
        page.goto("https://assets.test/")
        page.wait_for_load_state("load")
        context.close()
        return set(fulfilled)

    hidden = requests_made(block_styles=True)
    assert "logo.png" not in hidden and "site.css" not in hidden and "app.js" in hidden
    visible = requests_made(block_styles=False)
    assert "logo.png" not in visible and "site.css" in visible


# ---------- cleanup ----------

def _old(path: Path, days: int) -> Path:
    stamp = time.time() - days * 86_400
    os.utime(path, (stamp, stamp))
    return path


def test_cleanup_removes_old_files_but_protects_important_ones(tmp_path):
    data, uploads, output = tmp_path / "data", tmp_path / "uploads", tmp_path / "output"
    for folder in (data, uploads, output):
        folder.mkdir()
    old_resume = uploads / "old.pdf"; old_resume.write_text("x"); _old(old_resume, 40)
    new_resume = uploads / "new.pdf"; new_resume.write_text("x")
    daily_resume = uploads / "daily.pdf"; daily_resume.write_text("x"); _old(daily_resume, 90)
    old_report = output / "jobs_old.html"; old_report.write_text("x"); _old(old_report, 40)
    last_report = output / "jobs_last.html"; last_report.write_text("x"); _old(last_report, 40)
    last_excel = output / "jobs_last.xlsx"; last_excel.write_text("x"); _old(last_excel, 40)
    keep_note = output / "notes.txt"; keep_note.write_text("x"); _old(keep_note, 40)
    save_schedule(data, Schedule("09:00", search={"resume_path": str(daily_resume)}))
    save_state(data, last_run="2026-10-01T09:00:00", status="done", report=str(last_report))
    history = JobHistory(data / "history.sqlite3")
    history.set_status("linkedin", "1", "applied")
    cache = Cache(data / "cache.sqlite3")
    cache.save_descriptions([job("1", description="x")])
    with cache._connect() as db:
        db.execute("UPDATE descriptions SET saved_at = '2000-01-01T00:00:00'")

    result = cleanup(30, data, uploads, output, data / "cache.sqlite3")

    assert not old_resume.exists() and not old_report.exists()
    assert new_resume.exists() and daily_resume.exists()
    assert last_report.exists() and last_excel.exists() and keep_note.exists()
    assert (result.files, result.cache_rows) == (2, 1)
    assert history.counts()["applied"] == 1  # history is never touched


def test_cleanup_disabled_and_log_trim(tmp_path):
    uploads = tmp_path / "uploads"; uploads.mkdir()
    old = uploads / "old.pdf"; old.write_text("x"); _old(old, 400)
    assert cleanup(0, tmp_path, uploads, tmp_path / "output").files == 0
    assert old.exists()

    log = tmp_path / "scheduled.log"
    log.write_bytes(b"old line\n" * 400_000)  # ~3.6 MB
    assert cleanup(30, tmp_path, uploads, tmp_path / "output").log_trimmed
    assert log.stat().st_size <= 512 * 1024
    assert log.read_bytes().startswith(b"old line")


def test_keep_days_setting(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: None)
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

    monkeypatch.setattr(web, "JobMatcherLLM", FakeLLM)
    analyze = web.default_analyzer(Settings("key", history_path=tmp_path / "history.sqlite3"))
    first = tmp_path / "cv.txt"; first.write_text("Python developer")
    copy = tmp_path / "cv (1).txt"; copy.write_text("Python developer")

    assert analyze(first).skills == ["Python"]
    assert analyze(copy).skills == ["Python"]
    assert len(calls) == 1


def test_gives_up_on_a_site_that_keeps_failing(browser):
    context = browser.new_context()
    calls = []

    def fail(route):
        calls.append(route.request.url)
        route.abort("connectionfailed")

    context.route("**/seeMoreJobPostings/search*", fail)
    scraper = LinkedInScraper(context, delay_range=(0, 0))
    events = []

    jobs = pipeline.collect_jobs({"linkedin": scraper}, ["SDET", "QA"], ["Pune", "Delhi", "Remote"], lambda *a, **k: events.append(k))

    assert jobs == []
    # 6 searches planned; each failing search tries 3 times (1 + 2 retries); gives up after 2 searches.
    assert len(calls) == 2 * 3
    assert scraper.unreachable
    assert events[-1] == {"site": "linkedin", "status": "failed", "found": 0}
    context.close()


def test_one_success_resets_the_failure_count(browser, fixture_html):
    context = browser.new_context()
    html = fixture_html("linkedin_search.html")
    calls = []

    def flaky(route):
        calls.append(1)
        # Fails all 3 attempts of the first search, then works.
        if len(calls) <= 3:
            route.abort("connectionfailed")
        else:
            route.fulfill(body=html, content_type="text/html")

    context.route("**/seeMoreJobPostings/search*", flaky)
    # Short real waits: with none, the next load can race Chromium's error page from the aborted one.
    scraper = LinkedInScraper(context, delay_range=(0.3, 0.3))
    scraper.retry_delays = (0.3, 0.3)
    jobs = pipeline.collect_jobs({"linkedin": scraper}, ["SDET"], ["Pune", "Delhi", "Remote"])

    assert len(jobs) == 4  # Pune failed; Delhi and Remote each returned the 2 fixture cards
    assert not scraper.unreachable
    context.close()
