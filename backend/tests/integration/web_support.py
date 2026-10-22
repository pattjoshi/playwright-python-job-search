"""Fakes and helpers shared by the web API tests (the make_client fixture lives in conftest.py)."""

import io
import logging
import time

from job_search.models import Job, Profile, SearchResult
from job_search.services.matching_service import SearchStopped

PROFILE = Profile(
    current_title="QA Engineer",
    skills=["Python"],
    years_experience=4,
    locations=["Bangalore, Karnataka", "Pune"],
    search_queries=["SDET", "QA Automation"],
    summary="QA engineer",
)


class FakeRunner:
    """Stands in for search.run: records options, reports progress, returns canned results."""

    def __init__(self, output_dir, fail=False, block=None):
        self.output_dir = output_dir
        self.fail = fail
        self.block = block
        self.options = None

    def __call__(self, options, settings, on_event=None, stop_event=None):
        self.options = options
        on_event("stage", {"stage": "search"})
        on_event("funnel", {"steps": [("found", 169), ("unique", 120), ("scored", 3)]})
        on_event("site", {"site": "linkedin", "status": "running", "found": 0})
        if self.block:
            # Wait until the test releases us or presses Stop.
            while not self.block.is_set():
                if stop_event.is_set():
                    raise SearchStopped()
                time.sleep(0.01)
        logging.getLogger("job_search.services.search").info("LinkedIn: 'SDET' in 'Pune', page 1")
        on_event("profile", {"profile": options.profile, "queries": ["SDET"], "locations": ["Pune"]})
        if self.fail:
            raise ValueError("No text could be extracted from resume.pdf")
        html, xlsx, csv = (self.output_dir / name for name in ("r.html", "r.xlsx", "r.csv"))
        for path in (html, xlsx, csv):
            path.write_text("x")
        jobs = {
            site: [
                Job(site, f"{site}{i}", f"Job {i}", "Co", "Pune", f"https://example.com/{site}/{i}", score=90 - i, experience="1-3 Yrs")
                for i in range(count)
            ]
            for site, count in options.results_per_site.items()
        }
        all_jobs = [job for site_jobs in jobs.values() for job in site_jobs]
        return SearchResult(Profile(), all_jobs, jobs, html, xlsx, csv)


class FakeScheduler:
    kind = "windows"

    def __init__(self, fail=False):
        self.installed = None
        self.fail = fail

    def install(self, schedule):
        if self.fail:
            from job_search.services.schedule_service import ScheduleError

            raise ScheduleError("Access is denied.")
        self.installed = schedule

    def remove(self):
        self.installed = None



def upload(client, name="My Resume.txt", content=b"Python QA engineer"):
    return client.post("/api/analyze", files={"resume": (name, io.BytesIO(content), "text/plain")})


def search_body(resume_id, **overrides):
    body = {
        "resume_id": resume_id,
        "sites": {"linkedin": 20, "naukri": 12, "indeed": 10},
        "keywords": ["SDET", " QA  Automation ", "SDET"],
        "locations": ["Pune", "Remote"],
        "experience": [1, 2],
        "hours": 24,
        "only_new": True,
        "show_browser": True,
        "max_pages": 2,
        "top": 30,
    }
    body.update(overrides)
    return body


def start(client, **overrides):
    resume_id = upload(client).json()["resume_id"]
    return client.post("/api/search", json=search_body(resume_id, **overrides))


def wait_done(client, job_id):
    for _ in range(300):
        state = client.get(f"/api/search/{job_id}").json()
        if state["status"] not in ("running", "stopping"):
            return state
        time.sleep(0.01)
    raise AssertionError("search never finished")
