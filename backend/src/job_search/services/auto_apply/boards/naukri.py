"""Naukri: "Apply" sends the application at once, then a chat drawer may ask a few questions.

Because the first click already applies, a dry run only checks that you're signed in and Easy Apply is there.
"""

import re

from playwright.sync_api import Page

from job_search.services.auto_apply.applier import Outcome, take_screenshot
from job_search.services.auto_apply.boards.base import Board, _visible
from job_search.services.auto_apply.filler import Filler, pick

APPLY = re.compile(r"^\s*apply\s*$", re.I)
COMPANY_SITE = re.compile(r"apply on company (site|website)", re.I)
LOGIN_TO_APPLY = re.compile(r"(login|register) to apply", re.I)
ALREADY = re.compile(r"^\s*applied\s*$", re.I)
SENT = re.compile(r"successfully applied|you have applied|application (sent|submitted)", re.I)
DRAWER = ".chatbot_DrawerContentWrapper, [class*='chatbot_Drawer']"
QUESTION = ".botMsg, [class*='botMsg']"
OPTION = "input[type=radio], input[type=checkbox]"
TEXT = "[contenteditable='true'], .chatbot_InputContainer input, .chatbot_InputContainer textarea"
SEND = ".sendMsg, [class*='sendMsg'], button:has-text('Save'), button:has-text('Submit')"


class NaukriBoard(Board):
    name = "naukri"
    label = "Naukri"
    login_url = "https://www.naukri.com/nlogin/login"
    user_field = "#usernameField, input[placeholder*='Email' i]"
    password_field = "#passwordField, input[type=password]"

    def apply(self, page: Page, job_url: str, filler: Filler, dry_run: bool, screenshot) -> Outcome:
        page.goto(job_url, wait_until="domcontentloaded", timeout=45_000)
        buttons = (APPLY, ALREADY, COMPANY_SITE, LOGIN_TO_APPLY)
        self.wait_until(page, lambda: any(_visible(page.get_by_role("button", name=b)) for b in buttons), 20 if self.pace else 3)
        self.pause(page)
        if _visible(page.get_by_role("button", name=LOGIN_TO_APPLY)) or self.signed_out(page):
            return self.not_signed_in()
        if _visible(page.get_by_role("button", name=ALREADY)):
            return Outcome("submitted", "Already applied on Naukri.")
        if _visible(page.get_by_role("button", name=COMPANY_SITE)):
            return Outcome("blocked", "This job is applied to on the company's site, not on Naukri.")
        apply = _visible(page.get_by_role("button", name=APPLY))
        if not apply:
            return Outcome("failed", "Couldn't find Naukri's Apply button.", screenshot=take_screenshot(page, screenshot))
        if dry_run:
            return Outcome("filled", "Dry run: signed in and Easy Apply is available. (Naukri applies on the first click, "
                           "so nothing was clicked.)", screenshot=take_screenshot(page, screenshot))
        apply.click()
        return self._chat(page, filler, screenshot)

    def _chat(self, page: Page, filler: Filler, screenshot) -> Outcome:
        answers: list[dict] = []
        asked = ""
        for _ in range(self.max_steps):
            self.pause(page, 1.5, 3)
            if SENT.search(page.locator("body").inner_text()):
                return Outcome("submitted", "Submitted.", answers, take_screenshot(page, screenshot))
            drawer = page.locator(DRAWER)
            if not drawer.count() or not drawer.first.is_visible():
                continue
            questions = drawer.locator(QUESTION)
            question = questions.last.inner_text().strip() if questions.count() else ""
            if not question or question == asked:
                continue
            asked = question
            options = {box.get_attribute("value") or "": box for box in drawer.locator(OPTION).all()}
            labels = {_label(page, box) or value: box for value, box in options.items()}
            answer, how = filler.resolve(question, list(labels), True)
            if answer is None:
                return Outcome("needs_answer", f"Waiting for your answer to: {question} (the Naukri application is not complete)",
                               answers, take_screenshot(page, screenshot))
            if labels:
                chosen = pick(list(labels), answer)
                if chosen is None:
                    return Outcome("needs_answer", f"Your answer doesn't match Naukri's options for: {question}",
                                   answers, take_screenshot(page, screenshot))
                labels[chosen].check(force=True)
                answer = chosen
            else:
                box = drawer.locator(TEXT).first
                box.click()
                if box.evaluate("e => 'value' in e"):
                    box.fill(answer)
                else:  # a contenteditable chat box
                    page.keyboard.type(answer, delay=60)
            answers.append({"question": question, "answer": answer, "how": how})
            self.pause(page, 0.8, 2)
            drawer.locator(SEND).first.click()
        return Outcome("unconfirmed", "Applied on Naukri, but the questions didn't finish. Check the job on Naukri.",
                       answers, take_screenshot(page, screenshot))


def _label(page: Page, box) -> str:
    box_id = box.get_attribute("id")
    label = page.locator(f"label[for='{box_id}']") if box_id else None
    if label is not None and label.count():
        return label.first.inner_text().strip()
    return box.evaluate("e => (e.closest('label') || {}).innerText || ''").strip()
