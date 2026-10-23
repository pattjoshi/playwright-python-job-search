"""LinkedIn Easy Apply: a pop-up form of a few steps (Next → Review → Submit application)."""

import re
from urllib.parse import urlparse

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
EASY_BUTTON = ".jobs-apply-button:has-text('Easy Apply'), button[aria-label*='Easy Apply']"
APPLY = re.compile(r"^\s*apply( now)?\s*$|^apply on company website", re.I)
JOB_ID = re.compile(r"(\d{8,})")


class LinkedInBoard(Board):
    name = "linkedin"
    label = "LinkedIn"
    login_url = "https://www.linkedin.com/login"
    user_field = "#username"
    password_field = "#password"

    def apply(self, page: Page, job_url: str, filler: Filler, dry_run: bool, screenshot) -> Outcome:
        page.goto(job_page_url(job_url), wait_until="domcontentloaded", timeout=45_000)
        easy = lambda: _visible(page.get_by_role("button", name=EASY_APPLY)) or _visible(page.locator(EASY_BUTTON))  # noqa: E731
        other = lambda: _visible(page.get_by_role("button", name=APPLY)) or _visible(page.get_by_role("link", name=APPLY))  # noqa: E731
        # LinkedIn draws the Apply button a few seconds after the page loads.
        self.wait_until(page, lambda: bool(easy() or other() or self.signed_out(page)), 20 if self.pace else 3)
        self.pause(page)
        button = easy()
        if not button and APPLIED.search(page.locator("body").inner_text()):
            return Outcome("submitted", "Already applied on LinkedIn.")
        if not button and self.signed_out(page):
            return self.not_signed_in()
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


def job_page_url(url: str) -> str:
    """The signed-in job page (www.linkedin.com/jobs/view/<id>/) for any LinkedIn job link.

    Search results link to the public page (e.g. in.linkedin.com/jobs/view/title-at-company-<id>), which doesn't
    show Easy Apply even when you're signed in.
    """
    host = (urlparse(url).hostname or "").lower()
    found = JOB_ID.search(urlparse(url).path)
    if (host == "linkedin.com" or host.endswith(".linkedin.com")) and found:
        return f"https://www.linkedin.com/jobs/view/{found.group(1)}/"
    return url
