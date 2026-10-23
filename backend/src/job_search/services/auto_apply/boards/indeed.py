"""Indeed Apply: a few pages (Continue → Review your application → Submit your application), often in a new tab.

Indeed usually signs you in with a code sent by email: turn on Show browser the first time to type it.
"""

import re

from playwright.sync_api import Page

from job_search.services.auto_apply.applier import Outcome, take_screenshot
from job_search.services.auto_apply.boards.base import Board, _visible
from job_search.services.auto_apply.filler import Filler

APPLY = re.compile(r"^\s*apply now\s*$|^\s*easily apply\s*$", re.I)
COMPANY_SITE = re.compile(r"apply on company site", re.I)
NEXT = re.compile(r"^\s*(continue|next|review your application)\s*$", re.I)
SUBMIT = re.compile(r"^\s*submit( your application)?\s*$", re.I)
SENT = re.compile(r"application (has been |was )?submitted|your application has been sent", re.I)


class IndeedBoard(Board):
    name = "indeed"
    label = "Indeed"
    login_url = "https://secure.indeed.com/auth"

    def fill_login(self, page: Page, email: str, password: str) -> None:
        """Email first; then a password box if Indeed offers one (otherwise it emails you a code)."""
        page.locator(self.user_field).first.fill(email)
        self.pause(page, 0.5, 1.5)
        page.locator(self.user_field).first.press("Enter")
        page.wait_for_timeout(2_000)
        offer = _visible(page.get_by_role("link", name=re.compile(r"sign in with (a )?password", re.I)))
        if offer:
            offer.click()
            page.wait_for_timeout(1_000)
        if page.locator(self.password_field).count():
            page.locator(self.password_field).first.fill(password)
            self.pause(page, 0.5, 1.5)
            page.locator(self.password_field).first.press("Enter")

    def apply(self, page: Page, job_url: str, filler: Filler, dry_run: bool, screenshot) -> Outcome:
        page.goto(job_url, wait_until="domcontentloaded", timeout=45_000)
        loaded = lambda: any(_visible(page.get_by_role(role, name=b)) for role in ("button", "link") for b in (APPLY, COMPANY_SITE))  # noqa: E731
        self.wait_until(page, loaded, 20 if self.pace else 3)
        self.pause(page)
        if not loaded() and self.signed_out(page):
            return self.not_signed_in()
        if _visible(page.get_by_role("button", name=COMPANY_SITE)) or _visible(page.get_by_role("link", name=COMPANY_SITE)):
            return Outcome("blocked", "This job is applied to on the company's site, not on Indeed.")
        button = _visible(page.get_by_role("button", name=APPLY))
        if not button:
            return Outcome("failed", "Couldn't find Indeed's Apply now button.", screenshot=take_screenshot(page, screenshot))
        opened = len(page.context.pages)
        button.click()
        page.wait_for_timeout(2_000)
        if len(page.context.pages) > opened:
            page = page.context.pages[-1]
        page.wait_for_load_state("domcontentloaded")
        return self.step_through(page, lambda: page.locator("body"), filler, dry_run, screenshot, NEXT, SUBMIT, SENT)
