"""Parallel site searches and run history: these call the real search.run, which always
launches a real (fake-scraper-backed) Chromium browser via SiteSession."""

import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import job_search.services.search as search
from job_search.api.app import create_app
from job_search.config import Settings
from job_search.models import Job, Profile, SearchOptions, TokenUsage
from job_search.repositories import JobHistoryRepository
from job_search.services.matching_service import SearchStopped
from job_search.services.scraping import BaseScraper
from job_search.services.search import pipeline
from tests.auth_helpers import signed_in

SAMPLE_RESUME = Path(__file__).parent.parent / "sample_resume.txt"
TIMELINE: list = []


def make_site(name, delay=0.6, fail=False):
    class Site(BaseScraper):
        def search(self, query, location):
            TIMELINE.append((self.name, "start", time.monotonic(), threading.current_thread().name))
            time.sleep(delay)
            if fail:
                raise RuntimeError(f"{self.name} exploded")
            TIMELINE.append((self.name, "end", time.monotonic(), threading.current_thread().name))
            return [Job(self.name, f"{self.name}{i}", f"Python Dev {i}", f"{self.name} Co {i}", location, "u", "1 hour ago", 1,
                        description="Python") for i in range(3)]

        def pause(self):
            self.check_stop()

    Site.name = name
    return Site


class FakeLLM:
    def __init__(self, *args):
        self.usage = TokenUsage(calls=2, input_tokens=3000, cached_tokens=1000, output_tokens=500)

    def extract_profile(self, text):
        return Profile(skills=["Python"], search_queries=["Python Dev"], locations=["Pune"])

    def score_jobs(self, profile, jobs, experience=None, progress=None):
        for job in jobs:
            job.score = 70


def settings(**overrides):
    return Settings("key", "model", os.getenv("CHROMIUM_EXECUTABLE") or None, **overrides)


@pytest.fixture
def sites(monkeypatch):
    TIMELINE.clear()
    monkeypatch.setattr(pipeline, "JobMatcherLLM", FakeLLM)

    def use(**scrapers):
        monkeypatch.setattr(pipeline, "SCRAPERS", scrapers)
        return list(scrapers)

    return use


def window(site):
    start = next(t for s, kind, t, _ in TIMELINE if s == site and kind == "start")
    end = next(t for s, kind, t, _ in TIMELINE if s == site and kind == "end")
    return start, end


def test_sites_are_searched_at_the_same_time(tmp_path, sites):
    names = sites(linkedin=make_site("linkedin"), naukri=make_site("naukri"))
    options = SearchOptions(SAMPLE_RESUME, sites=names, output_dir=tmp_path, parallel_sites=True)

    result = search.run(options, settings())

    (a_start, a_end), (b_start, b_end) = window("linkedin"), window("naukri")
    assert b_start < a_end and a_start < b_end  # the two searches overlapped
    threads = {thread for *_, thread in TIMELINE}
    assert len(threads) == 2 and all("browser" in name for name in threads)  # one browser thread per site
    assert {job.source for job in result.jobs} == {"linkedin", "naukri"}


def test_sequential_mode(tmp_path, sites):
    names = sites(linkedin=make_site("linkedin", delay=0.2), naukri=make_site("naukri", delay=0.2))
    search.run(SearchOptions(SAMPLE_RESUME, sites=names, output_dir=tmp_path, parallel_sites=False), settings())
    assert window("naukri")[0] >= window("linkedin")[1]


def test_one_broken_site_does_not_stop_the_others(tmp_path, sites):
    names = sites(linkedin=make_site("linkedin", fail=True), naukri=make_site("naukri", delay=0.1))
    events = []

    result = search.run(SearchOptions(SAMPLE_RESUME, sites=names, output_dir=tmp_path), settings(),
                                 on_event=lambda name, data: events.append((name, data)))

    assert {job.source for job in result.jobs} == {"naukri"}
    assert ("site", {"site": "linkedin", "status": "failed", "found": 0}) in events
    assert result.stats.sites["naukri"]["status"] == "done"


def test_run_history_records_done_stopped_and_error(tmp_path, sites):
    names = sites(naukri=make_site("naukri", delay=0.05))
    history_path = tmp_path / "history.sqlite3"
    base = dict(sites=names, output_dir=tmp_path, history_path=history_path, origin="web", experience=(1, 3))

    done = search.run(SearchOptions(SAMPLE_RESUME, **base), settings(price_input=1.0, price_output=4.0, price_cached_input=0.5))

    stop = threading.Event()
    with pytest.raises(SearchStopped):
        search.run(SearchOptions(SAMPLE_RESUME, **base), settings(),
                            on_event=lambda name, data: stop.set() if name == "profile" else None, stop_event=stop)

    with pytest.raises(FileNotFoundError):
        search.run(SearchOptions(tmp_path / "missing.pdf", use_llm=False, keywords=["SDET"], **base), settings())

    runs = JobHistoryRepository(history_path).list_runs()
    assert [r["status"] for r in runs] == ["error", "stopped", "done"]  # newest first
    error, stopped, ok = runs
    assert "missing.pdf" in error["error"]
    assert ok["origin"] == "web" and ok["experience"] == [1, 3]
    assert ok["shown"] == 3 and ok["new"] == 3
    assert ok["sites"]["naukri"] == {"status": "done", "found": 3}
    assert ok["funnel"][0] == ["found", 3]
    assert ok["report"].endswith(".html")
    # 2000 uncached * $1 + 1000 cached * $0.5 + 500 out * $4, per 1M tokens
    assert ok["cost_usd"] == pytest.approx((2000 * 1 + 1000 * 0.5 + 500 * 4) / 1_000_000)
    assert ok["usage"]["calls"] == 2
    assert done.stats.duration_s >= 0
    assert stopped["sites"] and stopped["shown"] == 0


def test_runs_api(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    report = output / "jobs_1.html"
    report.write_text("x")
    history = JobHistoryRepository(tmp_path / "history.sqlite3")
    history.record_run("2026-10-02T09:00:00", "daily", "done", {"report": str(report), "shown": 5})
    history.record_run("2026-10-02T10:00:00", "web", "error", {"report": None, "error": "boom"})

    class NoScheduler:
        kind = "windows"

    app = create_app(Settings("key", history_path=tmp_path / "history.sqlite3"), output_dir=output,
                     upload_dir=tmp_path / "uploads", analyzer=lambda p: Profile(), system_scheduler=NoScheduler())
    body = signed_in(TestClient(app)).get("/api/runs").json()

    assert [r["status"] for r in body["runs"]] == ["error", "done"]
    assert body["runs"][1]["report_url"] == "/reports/jobs_1.html"
    assert body["runs"][0]["report_url"] is None
    assert body["costs_configured"] is False
