"""Full pipeline run with a fake job board and a fake OpenAI, so no network is needed."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import job_search.pipeline as pipeline
from job_search.config import Settings
from job_search.models import Job, Profile
from job_search.pipeline import SearchOptions, run
from job_search.scrapers.base import BaseScraper

SAMPLE_RESUME = Path(__file__).parent / "sample_resume.txt"


class FakeScraper(BaseScraper):
    name = "linkedin"

    def search(self, query, location):
        return [
            Job("linkedin", str(i), f"Python Engineer {i}", f"Company {i}", location, f"https://example.com/{i}", "1 hour ago", 1)
            for i in range(15)
        ]

    def fetch_description(self, job):
        job.description = "Python and Playwright" if int(job.job_id) % 2 == 0 else "Java"

    def pause(self):
        pass


class FakeLLM:
    def __init__(self, *args):
        pass

    def extract_profile(self, resume_text):
        return Profile(skills=["Python", "Playwright"], search_queries=["Python Engineer"], locations=["Pune"])

    def score_jobs(self, profile, jobs):
        for job in jobs:
            job.score = 100 - int(job.job_id)
            job.missing_skills = ["Docker"]


def test_run_writes_top_n_html(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SCRAPERS", {"linkedin": FakeScraper})
    monkeypatch.setattr(pipeline, "JobMatcherLLM", FakeLLM)
    settings = Settings("key", "model", os.getenv("CHROMIUM_EXECUTABLE") or None)
    options = SearchOptions(SAMPLE_RESUME, sites=["linkedin"], top_n=12, results_per_site=5, output_dir=tmp_path)

    # Own thread: other tests keep a sync Playwright instance open on the main thread.
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(run, options, settings).result()

    top = result.top_by_site["linkedin"]
    assert len(result.jobs) == 12
    assert [job.score for job in top] == sorted((job.score for job in top), reverse=True)
    assert len(top) == 5
    assert top[0].matched_skills == ["Python", "Playwright"]
    html = result.html_path.read_text(encoding="utf-8")
    assert "LinkedIn · top 5" in html
    assert result.xlsx_path.exists() and result.csv_path.exists()
