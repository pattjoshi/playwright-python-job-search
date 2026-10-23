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
from job_search.repositories.auto_apply_repository import COUNTED, AutoApplyRepository
from job_search.services.answers import AnswerAI, AnswerService
from job_search.services.applications import ApplicationService
from job_search.services.auto_apply.applier import Outcome, apply_one, take_screenshot
from job_search.services.auto_apply.boards import BOARDS
from job_search.services.auto_apply.browser import open_browser, write_docx
from job_search.services.auto_apply.filler import Filler
from job_search.services.auto_apply.platforms import detect
from job_search.services.auto_apply.rules import AutoApplyError, clean_settings, remaining_today, skipped_platforms
from job_search.services.auto_apply.sessions import SIGN_IN_WAIT_S, BoardSignIns, BrowserClosedError, is_closed_error, save_page

log = logging.getLogger(__name__)

MAX_DESCRIPTION = 6000  # characters kept per job, for the cover letter
CAPTCHA_WAIT_S = 120  # with the browser visible, time you get to solve a CAPTCHA, code or check
BOARD_GAP_S = (20, 45)  # seconds between two applications on the same board

__all__ = ["AutoApplyError", "AutoApplyService", "clean_settings", "open_browser", "write_docx"]


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
        self.sign_ins = BoardSignIns(self.files_dir)

    def save_settings(self, user_id: int, values: dict) -> dict:
        return self.repo.save_settings(user_id, clean_settings(values))

    def overview(self, user_id: int) -> dict:
        settings = self.repo.settings(user_id)
        done = self.repo.done_today(user_id, self.today().isoformat())
        signed = self.sign_ins.boards()
        boards = {board: {"today": done.get(board, 0), "has_login": board in self.board_logins, "signed_in": board in signed}
                  for board in BOARDS}
        jobs = [{**job, "has_page": (self.files_dir / f"{job['id']}.html").is_file()} for job in self.repo.for_user(user_id)]
        return {"settings": settings, "jobs": jobs, "today": sum(done.values()),
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
        for name in (job["screenshot"], f"{job_id}-cover-letter.docx", f"{job_id}.html"):
            if name:
                (self.files_dir / name).unlink(missing_ok=True)
        self.repo.delete(user_id, job_id)

    def screenshot(self, user_id: int, job_id: int) -> Path | None:
        name = self._get(user_id, job_id)["screenshot"]
        path = self.files_dir / name if name else None
        return path if path and path.is_file() else None

    def saved_page(self, user_id: int, job_id: int) -> Path | None:
        self._get(user_id, job_id)
        path = self.files_dir / f"{job_id}.html"
        return path if path.is_file() else None

    def sign_in(self, board: str, say: Callable[[str], None] = log.info) -> str | None:
        """Open the board's sign-in page in a visible browser and wait while you log in. None when signed in."""
        if board not in BOARDS:
            raise AutoApplyError("Unknown job board.", status=404)
        site = BOARDS[board](self.pace, SIGN_IN_WAIT_S, self.board_base_url)
        say(f"Sign in to {site.label} in the browser window that opened (you have {SIGN_IN_WAIT_S // 60} minutes).")
        with self.browser(False) as context:
            page = context.pages[0] if context.pages else context.new_page()
            problem = site.ensure_login(page, self.board_logins.get(board))
        if problem is None:
            self.sign_ins.mark(board)
        return problem

    def run(self, user_id: int, stop: threading.Event, say: Callable[[str], None] = log.info, only_job: int | None = None) -> int:
        """Apply to queued jobs, best match first, until the queue is empty, the limits are hit or you stop it.

        only_job: "Try this job": just that one, with the browser visible, whatever its place in the queue.
        """
        settings = self.repo.settings(user_id)
        if only_job is not None:
            self.retry(user_id, only_job)
            settings = {**settings, "show_browser": True}
        left = remaining_today(settings, self.repo.done_today(user_id, self.today().isoformat()))
        skip = {board for board in BOARDS if not settings[board] or not left[board]}
        if only_job is None and self.repo.next_queued(user_id, skipped_platforms(skip, left)) is None:
            limit_hit = not left["company"] and self.repo.next_queued(user_id, tuple(skip)) is not None
            say(f"Today's limit of {settings['daily_limit']} company-site applications is reached."
                if limit_hit else "Nothing is waiting in the queue.")
            return 0
        resume = self.resume_path()
        if not resume:
            raise AutoApplyError("Upload your resume on the Search jobs page first.")
        resume_text, ai, done, signed_in, last_board = self.resume_text() or "", self.ai_factory(), 0, set(), None
        say("Dry run: forms are filled but not submitted." if settings["dry_run"] else "Applying for real.")
        tried = False
        with self.browser(not settings["show_browser"]) as context:
            # One tab for the whole run: closing a visible browser's last tab closes the browser.
            page = context.pages[0] if context.pages else context.new_page()
            while not stop.is_set():
                if only_job is not None:
                    job, tried = (None if tried else self.repo.get(user_id, only_job)), True
                else:
                    job = self.repo.next_queued(user_id, skipped_platforms(skip, left))
                if job is None:
                    break
                board = job["platform"] if job["platform"] in BOARDS else None
                if board and board == last_board and self.pace and stop.wait(random.uniform(*BOARD_GAP_S) * self.pace):
                    break  # waiting between two applications on the same board, like a person would
                say(f"Applying: {job['title']} at {job['company']}")
                self.repo.update(user_id, job["id"], {"status": "running", "attempts": job["attempts"] + 1})
                try:
                    outcome, letter = self._apply(context, page, user_id, job, settings, ai, resume, resume_text, signed_in)
                except BrowserClosedError:
                    self.repo.update(user_id, job["id"], {"status": "queued"})
                    raise AutoApplyError("The auto-apply browser window was closed, so it stopped. Press Run now to go on.") from None
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

    def _apply(self, context: BrowserContext, page, user_id: int, job: dict, settings: dict, ai: AnswerAI | None,
               resume: Path, resume_text: str, signed_in: set[str]) -> tuple[Outcome, str]:
        def resolve(question: str, options: list[str], required: bool) -> tuple[str | None, str]:
            found = self.answers.resolve(user_id, question, options, f"{job['company']} · {job['title']}", add_if_missing=required)
            return found["answer"], found["how"]

        def write(question: str) -> str:
            if not (ai and resume_text):
                return ""
            return ai.write_for_job(question, job["title"], job["company"], job.get("description", ""), resume_text)

        filler = Filler(resolve, write, resume, lambda text: write_docx(self.files_dir / f"{job['id']}-cover-letter.docx", text))
        shot = self.files_dir / f"{job['id']}.png"
        wait_s = CAPTCHA_WAIT_S if settings["show_browser"] else 0
        try:
            if job["platform"] in BOARDS:
                board = BOARDS[job["platform"]](self.pace, wait_s, self.board_base_url)
                problem = None if board.name in signed_in else board.ensure_login(page, self.board_logins.get(board.name))
                if problem:
                    outcome = Outcome("blocked", problem, stop_platform=True)
                else:
                    signed_in.add(board.name)
                    self.sign_ins.mark(board.name)
                    outcome = board.apply(page, job["apply_url"], filler, settings["dry_run"], shot)
            else:
                outcome = apply_one(page, job["apply_url"], filler, settings["dry_run"], shot, captcha_wait_s=wait_s)
        except Exception as error:  # one broken page never stops the rest of the queue
            if is_closed_error(page, error):
                raise BrowserClosedError() from error
            log.exception("Auto-apply failed for %s", job["apply_url"])
            reason = (str(error).splitlines() or [error.__class__.__name__])[0][:200]
            outcome = Outcome("failed", f"Something went wrong: {reason}")
        finally:
            for extra in context.pages:  # tabs a site opened; the run's own tab stays open
                if extra is not page and not extra.is_closed():
                    extra.close()
        if outcome.status not in ("filled", "submitted") and not page.is_closed():
            outcome.screenshot = outcome.screenshot or take_screenshot(page, shot)
            save_page(page, self.files_dir / f"{job['id']}.html")
        return outcome, filler.cover_letter

    def _get(self, user_id: int, job_id: int) -> dict:
        job = self.repo.get(user_id, job_id)
        if job is None:
            raise AutoApplyError("That job isn't in your auto-apply list.", status=404)
        return job

