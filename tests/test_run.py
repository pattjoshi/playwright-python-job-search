"""Full pipeline runs with a fake job board and a fake OpenAI, so no network is needed."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import job_search.pipeline as pipeline
from job_search.config import Settings
from job_search.models import Job, Profile
from job_search.pipeline import SearchOptions, run
from job_search.scrapers.base import BaseScraper
from job_search.utils import SearchStopped

SAMPLE_RESUME = Path(__file__).parent / "sample_resume.txt"


class FakeScraper(BaseScraper):
    name = "linkedin"
    searched: list = []

    def search(self, query, location):
        FakeScraper.searched.append((query, location, self.experience))
        return [
            Job(
                "linkedin", str(i), f"Python Engineer {i}", f"Company {i}", location, f"https://example.com/{i}",
                "1 hour ago", 1, experience="8-12 Yrs" if i == 3 else "",
            )
            for i in range(15)
        ]

    def fetch_description(self, job):
        job.description = "Python and Playwright" if int(job.job_id) % 2 == 0 else "Java"

    def pause(self):
        self.check_stop()


class FakeLLM:
    def __init__(self, *args):
        self.experience = None

    def extract_profile(self, resume_text):
        return Profile(skills=["Python", "Playwright"], search_queries=["Python Engineer"], locations=["Pune, Maharashtra"])

    def score_jobs(self, profile, jobs, experience=None, before_batch=None):
        if before_batch:
            before_batch(0, len(jobs))
        for job in jobs:
            job.score = 100 - int(job.job_id)
            job.missing_skills = ["Docker"]


@pytest.fixture
def fake_board(monkeypatch):
    FakeScraper.searched = []
    monkeypatch.setattr(pipeline, "SCRAPERS", {"linkedin": FakeScraper})
    monkeypatch.setattr(pipeline, "JobMatcherLLM", FakeLLM)


def settings():
    return Settings("key", "model", os.getenv("CHROMIUM_EXECUTABLE") or None)


def run_in_thread(*args, **kwargs):
    # Own thread: other tests keep a sync Playwright instance open on the main thread.
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run, *args, **kwargs).result()


def test_run_writes_top_n_html(tmp_path, fake_board):
    options = SearchOptions(SAMPLE_RESUME, sites=["linkedin"], top_n=12, results_per_site={"linkedin": 5}, output_dir=tmp_path)

    result = run_in_thread(options, settings())

    top = result.top_by_site["linkedin"]
    assert len(result.jobs) == 12
    assert [job.score for job in top] == sorted((job.score for job in top), reverse=True)
    assert len(top) == 5
    assert top[0].matched_skills == ["Python", "Playwright"]
    # Location came from the resume, normalized to the city name.
    assert FakeScraper.searched == [("Python Engineer", "Pune", None)]
    html = result.html_path.read_text(encoding="utf-8")
    assert "LinkedIn · top 5" in html
    assert result.xlsx_path.exists() and result.csv_path.exists()


def test_run_with_locations_experience_and_events(tmp_path, fake_board):
    events = []
    options = SearchOptions(
        SAMPLE_RESUME,
        sites=["linkedin"],
        locations=["Bengaluru", "Remote"],
        experience=(1, 3),
        top_n=15,
        output_dir=tmp_path,
    )

    result = run_in_thread(options, settings(), on_event=lambda name, data: events.append((name, data)))

    assert [(q, loc) for q, loc, _ in FakeScraper.searched] == [("Python Engineer", "Bengaluru"), ("Python Engineer", "Remote")]
    assert FakeScraper.searched[0][2] == (1, 3)
    # Job 3 asks for 8-12 years, outside 1-3, so it's dropped.
    assert "3" not in {job.job_id for job in result.jobs}
    names = [name for name, _ in events]
    assert names[0] == "stage" and "profile" in names
    stages = [data["stage"] for name, data in events if name == "stage"]
    assert stages == ["resume", "search", "details", "score", "report"]
    assert ("site", {"site": "linkedin", "status": "done", "found": 30}) in events  # 15 per location
    funnels = [data["steps"] for name, data in events if name == "funnel"]
    assert funnels[0] == [("found", 30), ("unique", 15), ("posted in 24h", 15), ("match 1-3 yrs", 14)]
    assert funnels[-1][-2:] == [("checked", 14), ("scored", 14)]


def test_only_new_skips_jobs_seen_before(tmp_path, fake_board):
    history = tmp_path / "history.sqlite3"
    options = SearchOptions(
        SAMPLE_RESUME, sites=["linkedin"], top_n=15, results=4, history_path=history, output_dir=tmp_path
    )

    first = run_in_thread(options, settings())
    shown_first = {job.job_id for job in first.top_by_site["linkedin"]}
    assert all(job.is_new for job in first.top_by_site["linkedin"])

    options.only_new = True
    second = run_in_thread(options, settings())
    shown_second = {job.job_id for job in second.top_by_site["linkedin"]}

    assert len(shown_first) == len(shown_second) == 4
    assert shown_first.isdisjoint(shown_second)


def test_stop_before_search(tmp_path, fake_board):
    stop = threading.Event()

    def on_event(name, data):
        if name == "profile":
            stop.set()

    options = SearchOptions(SAMPLE_RESUME, sites=["linkedin"], output_dir=tmp_path)
    with pytest.raises(SearchStopped):
        run_in_thread(options, settings(), on_event=on_event, stop_event=stop)
    assert not list(tmp_path.glob("*.html"))
