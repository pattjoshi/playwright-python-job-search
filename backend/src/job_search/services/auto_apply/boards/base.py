"""What every job board's Easy Apply has in common: signing in, slow human-like pacing, security checks,
and stepping through a multi-page form (Next → Review → Submit).

Never guesses: a required question with no answer stops the application (it is left unsent).
"""

import logging
import random
import re
import time
from collections.abc import Callable

from playwright.sync_api import Locator, Page

from job_search.services.auto_apply.applier import Outcome, take_screenshot
from job_search.services.auto_apply.filler import Filler
from job_search.services.auto_apply.form_fields import read_form

log = logging.getLogger(__name__)

SECURITY_URL = re.compile(r"checkpoint|challenge|captcha|verify|security|otp", re.I)
CAPTCHA = "iframe[src*='captcha'], iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[title*='challenge'], #captcha"
SIGNED_OUT_URL = re.compile(r"/login|/signin|authwall|/uas/|nlogin", re.I)
SIGN_IN = re.compile(r"^\s*sign in( to apply)?\s*$", re.I)
ERRORS = "[role='alert']:visible, .artdeco-inline-feedback--error, [aria-invalid='true']"


class Board:
    """One board's Easy Apply. Subclasses set the URLs and selectors and implement apply()."""

    name = ""
    label = ""
    login_url = ""
    user_field = "input[type=email]"
    password_field = "input[type=password]"
    max_steps = 12

    def __init__(self, pace: float = 1.0, wait_for_you_s: float = 0, base_url: str | None = None):
        self.pace, self.wait_for_you_s = pace, wait_for_you_s
        if base_url:  # tests point the board at saved pages on a local server
            self.login_url = f"{base_url}/{self.name}_login.html"

    # ---------- pacing and checks ----------

    def pause(self, page: Page, low: float = 1.5, high: float = 4.0) -> None:
        """Wait like a person would between steps."""
        if self.pace:
            page.wait_for_timeout(random.uniform(low, high) * 1000 * self.pace)

    def security_check(self, page: Page) -> bool:
        return bool(SECURITY_URL.search(page.url)) or any(f.is_visible() for f in page.locator(CAPTCHA).all())

    def wait_until(self, page: Page, done: Callable[[], bool], seconds: float = 15) -> bool:
        """Poll until done() (e.g. the Apply button has loaded); pages like LinkedIn draw it late."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if done():
                return True
            page.wait_for_timeout(500)
        return done()

    def signed_out(self, page: Page) -> bool:
        """The page asks you to sign in (so applying can't work until you do)."""
        return bool(SIGNED_OUT_URL.search(page.url)) or bool(_visible(page.get_by_role("link", name=SIGN_IN))) \
            or bool(_visible(page.get_by_role("button", name=SIGN_IN)))

    def not_signed_in(self) -> Outcome:
        return Outcome("blocked", f"Not signed in to {self.label}. Press Sign in next to {self.label} in Auto-apply Settings "
                       "and log in once in the browser that opens.", stop_platform=True)

    def wait_for_you(self, page: Page, done: Callable[[], bool]) -> bool:
        """With the browser visible, give you time to finish a CAPTCHA / OTP / check; True once done()."""
        deadline = time.monotonic() + self.wait_for_you_s
        while time.monotonic() < deadline:
            if done():
                return True
            page.wait_for_timeout(1000)
        return done()

    # ---------- signing in ----------

    def ensure_login(self, page: Page, login: tuple[str, str] | None) -> str | None:
        """Sign in if needed. Returns None when signed in, else why not (shown on the page)."""
        page.goto(self.login_url, wait_until="domcontentloaded", timeout=45_000)
        self.pause(page, 1, 2)
        if not page.locator(self.password_field).count() and not page.locator(self.user_field).count():
            return None  # the saved profile is still signed in
        signed_in = lambda: not page.locator(self.password_field).count() and not self.security_check(page)  # noqa: E731
        if not login:  # no password saved: you sign in yourself in the open browser
            if self.wait_for_you_s and self.wait_for_you(page, signed_in):
                return None
            return (f"Not signed in to {self.label}. Press Sign in next to {self.label} in Auto-apply Settings and log in "
                    f"once in the browser that opens (or add {self.name.upper()}_EMAIL and _PASSWORD to .env).")
        self.fill_login(page, *login)
        if self.wait_until(page, signed_in, 10 if self.pace else 3):
            return None
        if self.wait_for_you_s and self.wait_for_you(page, signed_in):
            return None
        if self.security_check(page):
            return f"{self.label} asked for a security check or code. Turn on Show browser and run again to finish it once."
        return f"Couldn't sign in to {self.label}. Check the email and password in .env."

    def fill_login(self, page: Page, email: str, password: str) -> None:
        page.locator(self.user_field).first.fill(email)
        self.pause(page, 0.5, 1.5)
        page.locator(self.password_field).first.fill(password)
        self.pause(page, 0.5, 1.5)
        page.locator(self.password_field).first.press("Enter")

    # ---------- applying ----------

    def apply(self, page: Page, job_url: str, filler: Filler, dry_run: bool, screenshot) -> Outcome:
        raise NotImplementedError

    def step_through(self, page: Page, scope: Callable[[], Locator], filler: Filler, dry_run: bool, screenshot,
                     next_button: re.Pattern, submit_button: re.Pattern, sent: re.Pattern,
                     on_dry_run: Callable[[], None] = lambda: None) -> Outcome:
        """Fill each page of a multi-step form, clicking Next until Submit (which a dry run doesn't press)."""
        answers: list[dict] = []
        for _ in range(self.max_steps):
            self.pause(page, 1, 2.5)
            result = filler.fill(page, read_form(page, self.name))
            answers += result.answers
            if result.missing:
                shot = take_screenshot(page, screenshot)
                return Outcome("needs_answer", "Waiting for your answer to: " + "; ".join(result.missing[:5]), answers, shot)
            submit = _visible(scope().get_by_role("button", name=submit_button))
            if submit:
                shot = take_screenshot(page, screenshot)
                if dry_run:
                    on_dry_run()
                    return Outcome("filled", "Dry run: every step was filled; Submit was not pressed.", answers, shot)
                self.pause(page)
                submit.click()
                return self._confirm(page, sent, answers, shot)
            step = _visible(scope().get_by_role("button", name=next_button))
            if not step:
                return Outcome("failed", "Couldn't find the Next or Submit button.", answers, take_screenshot(page, screenshot))
            before = scope().inner_text()
            step.click()
            page.wait_for_timeout(800)
            errors = [e.inner_text().strip() for e in scope().locator(ERRORS).all() if e.is_visible() and e.inner_text().strip()]
            if errors and scope().inner_text() == before:
                return Outcome("failed", "The form showed errors: " + "; ".join(errors[:3]), answers, take_screenshot(page, screenshot))
        return Outcome("failed", "The application had more steps than expected.", answers, take_screenshot(page, screenshot))

    def _confirm(self, page: Page, sent: re.Pattern, answers: list[dict], shot: str) -> Outcome:
        for _ in range(30):
            page.wait_for_timeout(500)
            if sent.search(_text(page)):
                return Outcome("submitted", "Submitted.", answers, shot)
        return Outcome("unconfirmed", f"Submitted on {self.label}, but no confirmation was shown. Check your email.", answers, shot)


def _visible(locator: Locator) -> Locator | None:
    found = [item for item in locator.all() if item.is_visible() and item.is_enabled()]
    return found[-1] if found else None


def _text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5_000)
    except Exception:
        return ""
