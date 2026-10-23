"""Auto-apply rules: which jobs are queued, the safety settings, and working through the queue.

Safety: a daily limit, a minimum match score, and dry run (on by default) that fills forms without submitting.
Every filled form is screenshotted; submitted jobs go into the application tracker as Applied.
"""

import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright

from job_search.models import Job
from job_search.repositories.auto_apply_repository import COUNTED, SETTINGS, AutoApplyRepository
from job_search.services.answers import AnswerAI, AnswerService
from job_search.services.applications import ApplicationService
from job_search.services.auto_apply.applier import Outcome, apply_one
from job_search.services.auto_apply.filler import Filler
from job_search.services.auto_apply.platforms import detect

log = logging.getLogger(__name__)

MAX_DESCRIPTION = 6000  # characters kept per job, for the cover letter
CAPTCHA_WAIT_S = 120  # with the browser visible, time you get to solve a CAPTCHA
LIMITS = {"min_score": (0, 100), "daily_limit": (1, 100)}


class AutoApplyError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def clean_settings(values: dict) -> dict:
    """Validated settings from a request body (only the keys given). Raises AutoApplyError."""
    cleaned = {}
    for name in SETTINGS:
        if name not in values:
            continue
        value = values[name]
        if name in LIMITS:
            low, high = LIMITS[name]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise AutoApplyError(f"{name.replace('_', ' ').capitalize()} must be a whole number from {low} to {high}.")
        elif not isinstance(value, bool):
            raise AutoApplyError(f"{name.replace('_', ' ').capitalize()} must be true or false.")
        cleaned[name] = value
    return cleaned


@contextmanager
def open_browser(headless: bool, executable_path: str | None = None) -> Iterator[BrowserContext]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, executable_path=executable_path)
        try:
            yield browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        finally:
            browser.close()


def write_docx(path: Path, text: str) -> Path:
    import docx

    document = docx.Document()
    for paragraph in text.split("\n\n"):
        document.add_paragraph(paragraph.strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))
    return path


class AutoApplyService:
    def __init__(
        self,
        repo: AutoApplyRepository,
        answers: AnswerService,
        applications: ApplicationService,
        files_dir: Path,
        resume_path: Callable[[], Path | None],
        resume_text: Callable[[], str | None],
        ai_factory: Callable[[], AnswerAI | None] = lambda: None,
        browser: Callable[[bool], object] = open_browser,
        today: Callable[[], date] = date.today,
    ):
        self.repo, self.answers, self.applications, self.files_dir = repo, answers, applications, Path(files_dir)
        self.resume_path, self.resume_text, self.ai_factory = resume_path, resume_text, ai_factory
        self.browser, self.today = browser, today

    def save_settings(self, user_id: int, values: dict) -> dict:
        return self.repo.save_settings(user_id, clean_settings(values))

    def overview(self, user_id: int) -> dict:
        settings = self.repo.settings(user_id)
        done = self.repo.done_today(user_id, self.today().isoformat())
        return {"settings": settings, "jobs": self.repo.for_user(user_id), "today": done,
                "remaining": max(0, settings["daily_limit"] - done)}

    def queue_jobs(self, user_id: int, jobs: list[Job]) -> int:
        """Queue the jobs that link to a company application page and score at least the minimum."""
        min_score = self.repo.settings(user_id)["min_score"]
        items = [{
            "source": job.source, "source_job_id": job.job_id, "title": job.title, "company": job.company,
            "location": job.location, "job_url": job.url, "apply_url": job.apply_url, "platform": detect(job.apply_url),
            "score": job.score, "description": job.description[:MAX_DESCRIPTION],
        } for job in jobs if job.apply_url and job.score is not None and job.score >= min_score]
        return self.repo.enqueue(user_id, items)

    def retry(self, user_id: int, job_id: int) -> dict:
        self._get(user_id, job_id)
        return self.repo.update(user_id, job_id, {"status": "queued", "message": "", "finished_at": None})

    def remove(self, user_id: int, job_id: int) -> None:
        job = self._get(user_id, job_id)
        for name in (job["screenshot"], f"{job_id}-cover-letter.docx"):
            if name:
                (self.files_dir / name).unlink(missing_ok=True)
        self.repo.delete(user_id, job_id)

    def screenshot(self, user_id: int, job_id: int) -> Path | None:
        name = self._get(user_id, job_id)["screenshot"]
        path = self.files_dir / name if name else None
        return path if path and path.is_file() else None

    def run(self, user_id: int, stop: threading.Event, say: Callable[[str], None] = log.info) -> int:
        """Apply to queued jobs, best match first, until the queue is empty, the daily limit is hit or you stop it."""
        settings, overview = self.repo.settings(user_id), self.overview(user_id)
        remaining = overview["remaining"]
        if not remaining:
            say(f"Today's limit of {settings['daily_limit']} applications is reached.")
            return 0
        if self.repo.next_queued(user_id) is None:
            say("Nothing is waiting in the queue.")
            return 0
        resume = self.resume_path()
        if not resume:
            raise AutoApplyError("Upload your resume on the Search jobs page first.")
        resume_text, ai, done = self.resume_text() or "", self.ai_factory(), 0
        say(("Dry run: forms are filled but not submitted. " if settings["dry_run"] else "") + f"Up to {remaining} today.")
        with self.browser(not settings["show_browser"]) as context:
            while remaining > done and not stop.is_set():
                job = self.repo.next_queued(user_id)
                if job is None:
                    break
                say(f"Applying: {job['title']} at {job['company']}")
                self.repo.update(user_id, job["id"], {"status": "running", "attempts": job["attempts"] + 1})
                outcome, letter = self._apply(context, user_id, job, settings, ai, resume, resume_text)
                self.repo.update(user_id, job["id"], {
                    "status": outcome.status, "message": outcome.message, "answers": outcome.answers,
                    "screenshot": outcome.screenshot, "cover_letter": letter,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                })
                if outcome.status in ("submitted", "unconfirmed"):
                    self.applications.track_job(user_id, {**job, "job_id": job["source_job_id"], "url": job["job_url"]}, "applied")
                done += outcome.status in COUNTED
                say(f"{job['company']}: {outcome.message}")
        return done

    def _apply(self, context: BrowserContext, user_id: int, job: dict, settings: dict, ai: AnswerAI | None,
               resume: Path, resume_text: str) -> tuple[Outcome, str]:
        def resolve(question: str, options: list[str], required: bool) -> tuple[str | None, str]:
            found = self.answers.resolve(user_id, question, options, f"{job['company']} · {job['title']}", add_if_missing=required)
            return found["answer"], found["how"]

        def write(question: str) -> str:
            if not (ai and resume_text):
                return ""
            return ai.write_for_job(question, job["title"], job["company"], job.get("description", ""), resume_text)

        filler = Filler(resolve, write, resume, lambda text: write_docx(self.files_dir / f"{job['id']}-cover-letter.docx", text))
        page = context.new_page()
        try:
            outcome = apply_one(page, job["apply_url"], filler, settings["dry_run"], self.files_dir / f"{job['id']}.png",
                                captcha_wait_s=CAPTCHA_WAIT_S if settings["show_browser"] else 0)
        except Exception as error:  # one broken page never stops the rest of the queue
            log.exception("Auto-apply failed for %s", job["apply_url"])
            reason = (str(error).splitlines() or [error.__class__.__name__])[0][:200]
            outcome = Outcome("failed", f"Something went wrong: {reason}")
        finally:
            for open_page in context.pages:
                open_page.close()
        return outcome, filler.cover_letter

    def _get(self, user_id: int, job_id: int) -> dict:
        job = self.repo.get(user_id, job_id)
        if job is None:
            raise AutoApplyError("That job isn't in your auto-apply list.", status=404)
        return job
