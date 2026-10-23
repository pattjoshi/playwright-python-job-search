"""Auto-apply rules: which jobs are queued, the safety settings, and working through the queue.

Two kinds of jobs:
  company sites     the board links to the company's own application page (Greenhouse, Lever, ...)
  board Easy Apply  applied to on Naukri / LinkedIn / Indeed themselves, with your login (off until you turn a board on)
Safety: dry run (on by default), a daily limit for company sites and a smaller one per board, a minimum match
score, and slow human-like pacing on the boards. Every filled form is screenshotted; submitted jobs go into
the application tracker as Applied.
"""

import logging
import random
import threading
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import BrowserContext

from job_search.models import Job
from job_search.repositories.auto_apply_repository import COUNTED, SETTINGS, AutoApplyRepository
from job_search.services.answers import AnswerAI, AnswerService
from job_search.services.applications import ApplicationService
from job_search.services.auto_apply.applier import Outcome, apply_one
from job_search.services.auto_apply.boards import BOARDS
from job_search.services.auto_apply.browser import open_browser, write_docx
from job_search.services.auto_apply.filler import Filler
from job_search.services.auto_apply.platforms import PLATFORMS, detect

log = logging.getLogger(__name__)

MAX_DESCRIPTION = 6000  # characters kept per job, for the cover letter
CAPTCHA_WAIT_S = 120  # with the browser visible, time you get to solve a CAPTCHA, code or check
BOARD_GAP_S = (20, 45)  # seconds between two applications on the same board
LIMITS = {"min_score": (0, 100), "daily_limit": (1, 100), "board_daily_limit": (1, 50)}
COMPANY_PLATFORMS = (*PLATFORMS, "other")

__all__ = ["AutoApplyError", "AutoApplyService", "clean_settings", "open_browser", "write_docx"]


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


def remaining_today(settings: dict, done: dict[str, int]) -> dict[str, int]:
    """{"company": n, "naukri": n, ...}: how many more applications each kind may send today."""
    company_done = sum(count for platform, count in done.items() if platform not in BOARDS)
    left = {"company": max(0, settings["daily_limit"] - company_done)}
    left.update({board: max(0, settings["board_daily_limit"] - done.get(board, 0)) for board in BOARDS})
    return left


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
        board_logins: dict[str, tuple[str, str]] | None = None,
        pace: float = 1.0,
        board_base_url: str | None = None,
    ):
        self.repo, self.answers, self.applications, self.files_dir = repo, answers, applications, Path(files_dir)
        self.resume_path, self.resume_text, self.ai_factory = resume_path, resume_text, ai_factory
        self.browser, self.today = browser, today
        self.board_logins, self.pace, self.board_base_url = board_logins or {}, pace, board_base_url

    def save_settings(self, user_id: int, values: dict) -> dict:
        return self.repo.save_settings(user_id, clean_settings(values))

    def overview(self, user_id: int) -> dict:
        settings = self.repo.settings(user_id)
        done = self.repo.done_today(user_id, self.today().isoformat())
        boards = {board: {"today": done.get(board, 0), "has_login": board in self.board_logins} for board in BOARDS}
        return {"settings": settings, "jobs": self.repo.for_user(user_id), "today": sum(done.values()),
                "remaining": remaining_today(settings, done)["company"], "boards": boards}

    def queue_jobs(self, user_id: int, jobs: list[Job]) -> int:
        """Queue matches at or above the minimum score: company-site jobs, and Easy Apply jobs on boards you turned on."""
        settings = self.repo.settings(user_id)
        items = []
        for job in jobs:
            if job.score is None or job.score < settings["min_score"]:
                continue
            if job.apply_url:
                link, platform = job.apply_url, detect(job.apply_url)
            elif job.source in BOARDS and settings.get(job.source) and job.url:
                link, platform = job.url, job.source
            else:
                continue
            items.append({"source": job.source, "source_job_id": job.job_id, "title": job.title, "company": job.company,
                          "location": job.location, "job_url": job.url, "apply_url": link, "platform": platform,
                          "score": job.score, "description": job.description[:MAX_DESCRIPTION]})
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
        """Apply to queued jobs, best match first, until the queue is empty, the limits are hit or you stop it."""
        settings = self.repo.settings(user_id)
        left = remaining_today(settings, self.repo.done_today(user_id, self.today().isoformat()))
        skip = {board for board in BOARDS if not settings[board] or not left[board]}
        if self.repo.next_queued(user_id, _skipped(skip, left)) is None:
            limit_hit = not left["company"] and self.repo.next_queued(user_id, tuple(skip)) is not None
            say(f"Today's limit of {settings['daily_limit']} company-site applications is reached."
                if limit_hit else "Nothing is waiting in the queue.")
            return 0
        resume = self.resume_path()
        if not resume:
            raise AutoApplyError("Upload your resume on the Search jobs page first.")
        resume_text, ai, done, signed_in, last_board = self.resume_text() or "", self.ai_factory(), 0, set(), None
        say("Dry run: forms are filled but not submitted." if settings["dry_run"] else "Applying for real.")
        with self.browser(not settings["show_browser"]) as context:
            while not stop.is_set():
                job = self.repo.next_queued(user_id, _skipped(skip, left))
                if job is None:
                    break
                board = job["platform"] if job["platform"] in BOARDS else None
                if board and board == last_board and self.pace and stop.wait(random.uniform(*BOARD_GAP_S) * self.pace):
                    break  # waiting between two applications on the same board, like a person would
                say(f"Applying: {job['title']} at {job['company']}")
                self.repo.update(user_id, job["id"], {"status": "running", "attempts": job["attempts"] + 1})
                outcome, letter = self._apply(context, user_id, job, settings, ai, resume, resume_text, signed_in)
                self.repo.update(user_id, job["id"], {
                    "status": outcome.status, "message": outcome.message, "answers": outcome.answers,
                    "screenshot": outcome.screenshot, "cover_letter": letter,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                })
                if outcome.status in ("submitted", "unconfirmed"):
                    self.applications.track_job(user_id, {**job, "job_id": job["source_job_id"], "url": job["job_url"]}, "applied")
                kind = board or "company"
                if outcome.status in COUNTED:
                    done, left[kind] = done + 1, left[kind] - 1
                if board and (outcome.stop_platform or not left[board]):
                    skip.add(board)
                last_board = board
                say(f"{job['company']}: {outcome.message}")
        return done

    def _apply(self, context: BrowserContext, user_id: int, job: dict, settings: dict, ai: AnswerAI | None,
               resume: Path, resume_text: str, signed_in: set[str]) -> tuple[Outcome, str]:
        def resolve(question: str, options: list[str], required: bool) -> tuple[str | None, str]:
            found = self.answers.resolve(user_id, question, options, f"{job['company']} · {job['title']}", add_if_missing=required)
            return found["answer"], found["how"]

        def write(question: str) -> str:
            if not (ai and resume_text):
                return ""
            return ai.write_for_job(question, job["title"], job["company"], job.get("description", ""), resume_text)

        filler = Filler(resolve, write, resume, lambda text: write_docx(self.files_dir / f"{job['id']}-cover-letter.docx", text))
        page, shot = context.new_page(), self.files_dir / f"{job['id']}.png"
        wait_s = CAPTCHA_WAIT_S if settings["show_browser"] else 0
        try:
            if job["platform"] in BOARDS:
                board = BOARDS[job["platform"]](self.pace, wait_s, self.board_base_url)
                problem = None if board.name in signed_in else board.ensure_login(page, self.board_logins.get(board.name))
                if problem:
                    return Outcome("blocked", problem, stop_platform=True), ""
                signed_in.add(board.name)
                outcome = board.apply(page, job["apply_url"], filler, settings["dry_run"], shot)
            else:
                outcome = apply_one(page, job["apply_url"], filler, settings["dry_run"], shot, captcha_wait_s=wait_s)
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


def _skipped(skip: set[str], left: dict[str, int]) -> tuple[str, ...]:
    """Platforms not to pick from now: boards that are off, signed out or at their limit; company sites at theirs."""
    return (*skip, *(() if left["company"] else COMPANY_PLATFORMS))
