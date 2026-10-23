"""Apply to one job on its career page: open it, find the form, fill it, take a screenshot, submit, check it went through."""

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Page

from job_search.services.auto_apply.filler import Filler
from job_search.services.auto_apply.form_fields import read_form
from job_search.services.auto_apply.platforms import NAMES, NEEDS_ACCOUNT, detect, form_url

log = logging.getLogger(__name__)

APPLY_BUTTON = re.compile(
    r"^\s*(apply( now| here| online| for this (job|position|role))?|i'?m interested|start (your )?application)\s*$", re.I)
SUBMIT_BUTTON = re.compile(r"submit|send( my)? application|^\s*apply( now)?\s*$", re.I)
CONFIRMED_TEXT = re.compile(
    r"thank(s| you) for (applying|your application)|application (was |has been )?(received|submitted|sent)"
    r"|we('ve| have) received your|successfully (submitted|applied)", re.I)
CONFIRMED_URL = re.compile(r"confirm|thank|success|submitted", re.I)
CAPTCHA = "iframe[src*='hcaptcha'], iframe[title*='challenge'], iframe[src*='recaptcha/api2/bframe'], iframe[src*='turnstile']"
ERRORS = "[aria-invalid='true'], .field-error, .error-message, [class*='error-message'], [role='alert']"
MIN_FIELDS = 2  # fewer than this is a search box or newsletter sign-up, not an application form


@dataclass
class Outcome:
    status: str  # filled | submitted | unconfirmed | needs_answer | blocked | failed
    message: str
    answers: list[dict] = field(default_factory=list)
    screenshot: str = ""
    stop_platform: bool = False  # e.g. the board login failed: don't try its other jobs this run


def apply_one(page: Page, apply_url: str, filler: Filler, dry_run: bool, screenshot: Path,
              timeout_ms: int = 45_000, captcha_wait_s: float = 0, confirm_s: float = 20) -> Outcome:
    """captcha_wait_s > 0 (browser visible) gives you that long to solve a CAPTCHA after submitting."""
    platform = detect(apply_url)
    if platform in NEEDS_ACCOUNT:
        return _needs_account(platform)
    page.goto(form_url(apply_url, platform), wait_until="domcontentloaded", timeout=timeout_ms)
    _settle(page)
    platform = detect(page.url) if detect(page.url) != "other" else platform  # where the redirects ended up
    if platform in NEEDS_ACCOUNT:
        return _needs_account(platform)
    fields = read_form(page, platform)
    if len(fields) < MIN_FIELDS:
        page = _click_apply(page)
        fields = read_form(page, platform)
    if len(fields) < MIN_FIELDS:
        if page.locator("input[type=password]:visible").count():
            return Outcome("blocked", "The site asks you to sign in first, so apply there yourself.")
        return Outcome("failed", "Couldn't find an application form on the page.")

    log.info("Filling %d fields on %s (%s)", len(fields), page.url, NAMES.get(platform, platform))
    result = filler.fill(page, fields)
    shot = take_screenshot(page, screenshot)
    if result.missing:
        asked = "; ".join(result.missing[:5]) + ("…" if len(result.missing) > 5 else "")
        return Outcome("needs_answer", f"Waiting for your answer to: {asked}", result.answers, shot)
    if dry_run:
        return Outcome("filled", "Dry run: the form was filled but not submitted.", result.answers, shot)
    before = _body_text(page)
    if not _submit(page):
        return Outcome("failed", "Couldn't find the form's submit button.", result.answers, shot)
    status, message = _confirm(page, before, captcha_wait_s, confirm_s)
    return Outcome(status, message, result.answers, shot)


def _needs_account(platform: str) -> Outcome:
    return Outcome("blocked", f"{NAMES[platform]} needs an account for each company, so apply there yourself.")


def _settle(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=8_000)
    except Exception:  # pages that keep polling never go idle; what's loaded is enough
        pass


def _click_apply(page: Page) -> Page:
    """Click the page's "Apply" button; returns the page the form is on (it may open in a new tab)."""
    for role in ("link", "button"):
        button = page.get_by_role(role, name=APPLY_BUTTON)
        visible = [b for b in button.all() if b.is_visible()]
        if not visible:
            continue
        opened = len(page.context.pages)
        visible[0].click()
        page.wait_for_timeout(1_500)
        if len(page.context.pages) > opened:
            page = page.context.pages[-1]
        _settle(page)
        return page
    return page


def _submit(page: Page) -> bool:
    form = page.locator("[data-ja-form]")
    for candidates in (form.locator("button[type=submit], input[type=submit]"), form.get_by_role("button", name=SUBMIT_BUTTON),
                       page.get_by_role("button", name=SUBMIT_BUTTON)):
        visible = [b for b in candidates.all() if b.is_visible()]
        if visible:
            visible[-1].click()
            return True
    return False


def _confirm(page: Page, before: str, captcha_wait_s: float, confirm_s: float) -> tuple[str, str]:
    url_before = page.url
    deadline, waited_for_you = time.monotonic() + confirm_s, False
    while time.monotonic() < deadline:
        page.wait_for_timeout(500)
        text = _body_text(page)
        if CONFIRMED_TEXT.search(text) and not CONFIRMED_TEXT.search(before):
            return "submitted", "Submitted."
        if page.url != url_before and CONFIRMED_URL.search(page.url):
            return "submitted", "Submitted."
        if captcha_wait_s and not waited_for_you and page.locator(CAPTCHA).count():
            deadline, waited_for_you = time.monotonic() + captcha_wait_s, True  # time to solve it in the open browser
    if any(frame.is_visible() for frame in page.locator(CAPTCHA).all()):
        return "blocked", "A CAPTCHA appeared after submitting. Turn on Show browser to solve it while auto-apply runs."
    errors = [e.inner_text().strip() for e in page.locator(ERRORS).all() if e.is_visible() and e.inner_text().strip()]
    if errors:
        return "failed", "The form showed errors: " + "; ".join(errors[:3])
    if not page.locator("[data-ja-form]").count():
        return "unconfirmed", "The form went away but no confirmation was shown. Check your email."
    return "unconfirmed", "Submitted, but no confirmation was shown. Check your email."


def _body_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5_000)
    except Exception:
        return ""


def take_screenshot(page: Page, path: Path) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        return path.name
    except Exception as error:  # a missing screenshot never fails the application
        log.warning("Couldn't take a screenshot: %s", error)
        return ""

