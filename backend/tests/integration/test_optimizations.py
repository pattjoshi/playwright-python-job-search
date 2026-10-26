"""Tests for the speed / cost / reliability work that need a real browser or a full pipeline run."""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import job_search.services.search as search
from job_search.config import Settings
from job_search.models import Job, Profile, SearchOptions
from job_search.services.matching_service import SearchStopped
from job_search.services.scraping import BaseScraper
from job_search.services.scraping.browser import block_assets
from job_search.services.scraping.linkedin import LinkedInScraper
from job_search.services.search import pipeline

SAMPLE_RESUME = Path(__file__).parent.parent / "sample_resume.txt"


def job(job_id, source="linkedin", **kwargs):
    return Job(source, job_id, f"Python Engineer {job_id}", "Co", "Pune", f"https://example.com/{job_id}", **kwargs)


# ---------- pipeline reuses cached work ----------

class CountingScraper(BaseScraper):
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
        return executor.submit(search.run, *args, **kwargs).result()


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


# ---------- scrapers: retry on 429 ----------

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


# ---------- scraper failure counting ----------

def test_gives_up_on_a_site_that_keeps_failing(browser):
    context = browser.new_context()
    calls = []

    def fail(route):
        calls.append(route.request.url)
        route.abort("connectionfailed")

    context.route("**/seeMoreJobPostings/search*", fail)
    scraper = LinkedInScraper(context, delay_range=(0, 0))
    events = []

    jobs = search.collect_jobs({"linkedin": scraper}, ["SDET", "QA"], ["Pune", "Delhi", "Remote"], lambda *a, **k: events.append(k))

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
    jobs = search.collect_jobs({"linkedin": scraper}, ["SDET"], ["Pune", "Delhi", "Remote"])

    assert len(jobs) == 4  # Pune failed; Delhi and Remote each returned the 2 fixture cards
    assert not scraper.unreachable
    context.close()
