"""LinkedIn Easy Apply: a pop-up form of a few steps (Next → Review → Submit application)."""

import re

from playwright.sync_api import Page

from job_search.services.auto_apply.applier import Outcome, take_screenshot
from job_search.services.auto_apply.boards.base import Board, _visible
from job_search.services.auto_apply.filler import Filler

EASY_APPLY = re.compile(r"easy apply", re.I)
APPLIED = re.compile(r"applied \d+ |application submitted|you applied", re.I)
NEXT = re.compile(r"^\s*(next|continue|review)( to next step| your application)?\s*$", re.I)
SUBMIT = re.compile(r"^\s*submit( application)?\s*$", re.I)
SENT = re.compile(r"application (was )?sent|your application was sent", re.I)
DIALOG = ".jobs-easy-apply-modal, [role='dialog']"


class LinkedInBoard(Board):
    name = "linkedin"
    label = "LinkedIn"
    login_url = "https://www.linkedin.com/login"
    user_field = "#username"
    password_field = "#password"

    def apply(self, page: Page, job_url: str, filler: Filler, dry_run: bool, screenshot) -> Outcome:
        page.goto(job_url, wait_until="domcontentloaded", timeout=45_000)
        self.pause(page)
        if APPLIED.search(page.locator("body").inner_text()) and not _visible(page.get_by_role("button", name=EASY_APPLY)):
            return Outcome("submitted", "Already applied on LinkedIn.")
        button = _visible(page.get_by_role("button", name=EASY_APPLY))
        if not button:
            return Outcome("blocked", "No Easy Apply on this job (it's applied to on the company's site).",
                           screenshot=take_screenshot(page, screenshot))
        button.click()
        page.locator(DIALOG).first.wait_for(timeout=15_000)
        dialog = lambda: page.locator(DIALOG).first  # noqa: E731
        return self.step_through(page, dialog, filler, dry_run, screenshot, NEXT, SUBMIT, SENT,
                                 on_dry_run=lambda: self._discard(page))

    def _discard(self, page: Page) -> None:
        """Close the pop-up without sending (a dry run)."""
        close = _visible(page.get_by_role("button", name=re.compile(r"dismiss|close", re.I)))
        if close:
            close.click()
            discard = _visible(page.get_by_role("button", name=re.compile(r"^\s*discard\s*$", re.I)))
            if discard:
                discard.click()
