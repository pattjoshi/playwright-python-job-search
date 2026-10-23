"""Builds an AutoApplyService on a temporary database with a fake AI (shared by unit and integration tests)."""

from contextlib import contextmanager
from datetime import date

from job_search.repositories import AnswerRepository, ApplicationRepository, AutoApplyRepository, UserRepository
from job_search.services.answers import AnswerService
from job_search.services.applications import ApplicationService
from job_search.services.auto_apply import AutoApplyService
from tests.answer_fakes import fake_ai

RESUME_TEXT = "Om Prakash · om@example.com · QA engineer, 3 years Python and Playwright"


def browser_factory(browser):
    """Auto-apply's browser for tests: a fresh context on the session's shared browser.

    (In the app auto-apply starts its own browser on its own thread; a second one can't start on the test's thread.)
    """
    @contextmanager
    def open_context(_headless):
        context = browser.new_context()
        try:
            yield context
        finally:
            context.close()

    return open_context


def make_service(tmp_path, browser=None, resume=True, **options):
    path = tmp_path / "h.sqlite3"
    UserRepository(path).create("om@example.com", "Om", "x", "owner")
    resume_file = tmp_path / "cv.pdf"
    resume_file.write_bytes(b"%PDF-1.4")
    _, ai = fake_ai()
    answers = AnswerService(AnswerRepository(path), lambda: ai, lambda: RESUME_TEXT)
    return AutoApplyService(
        AutoApplyRepository(path), answers, ApplicationService(ApplicationRepository(path)), tmp_path / "auto-apply",
        lambda: resume_file if resume else None, lambda: RESUME_TEXT, lambda: ai,
        browser or (lambda headless: None), today=lambda: date.today(), **options,
    )
