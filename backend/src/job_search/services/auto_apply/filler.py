"""Decide what goes in each form field, and put it there.

  resume / CV upload           -> your resume file
  cover letter, "why join us?" -> written by the AI for this job
  first / last / full name     -> from your Answer Bank's "Full name"
  anything else                -> the Answer Bank (saved, matched, drafted, or added as "needs answer")
A required field with no answer is reported as missing (and added to the Answer Bank), and the form is not submitted.
An optional field you have no answer for is left empty and not added.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Page

from job_search.services.answers.matching import normalize
from job_search.services.auto_apply.form_fields import FormField

log = logging.getLogger(__name__)

TEXT_KINDS = {"text", "email", "tel", "url", "number", "date", "textarea"}
_RESUME = re.compile(r"\b(resume|résumé|cv|curriculum)\b")
_COVER = re.compile(r"\b(cover|motivation) letter\b")
_WHY = re.compile(r"why (do|would) you (want|like)|why are you interested|why (this|our|us)\b|what (interests|excites|attracts) you")
_FIRST = re.compile(r"^(legal |preferred )?(first|given) name$|^preferred name$")
_LAST = re.compile(r"^(legal )?(last|family) name$|^surname$")
_FULL = re.compile(r"^(your |legal )?(full )?name$")
MAX_LOGGED = 500  # characters of each answer kept in the log
FILE_LABELS = {"resume": "Your resume file", "ai_letter": "Cover letter written by AI (Word file)"}


@dataclass
class FillResult:
    answers: list[dict] = field(default_factory=list)  # {"question", "answer", "how"}
    missing: list[str] = field(default_factory=list)  # required questions left empty


def pick(options: list[str], answer: str) -> str | None:
    """The option an answer means: exact, then starting with the same words, then containing them."""
    wanted = normalize(answer).split()
    if not wanted:
        return None
    words = {option: normalize(option).split() for option in options}
    for test in (
        lambda w: w == wanted,
        lambda w: w[: len(wanted)] == wanted,
        lambda w: len(w) > 0 and wanted[: len(w)] == w,
        lambda w: " ".join(wanted) in " ".join(w),
    ):
        found = [option for option, w in words.items() if test(w)]
        if found:
            return found[0]
    return None


def _is_yes(value: str) -> bool:
    return normalize(value) in ("yes", "y", "true", "i agree", "agree")


class Filler:
    """Answers the fields of one job's form."""

    def __init__(
        self,
        resolve: Callable[[str, list[str], bool], tuple[str | None, str]],  # (question, options, required)
        write_for_job: Callable[[str], str] | None,
        resume_path: Path | None,
        cover_letter_file: Callable[[str], Path],
    ):
        self.resolve, self.write_for_job = resolve, write_for_job
        self.resume_path, self.cover_letter_file = resume_path, cover_letter_file
        self.cover_letter = ""
        self._written: dict[str, str] = {}

    def decide(self, f: FormField) -> tuple[str | None, str]:
        """(value, how) for one field; value None means "leave it empty"."""
        label = normalize(f.label)
        if f.kind == "file":
            if _COVER.search(label):
                text = self._write("Cover letter")
                return (str(self.cover_letter_file(text)), "ai_letter") if text else (None, "")
            if _RESUME.search(label) or _RESUME.search(normalize(f.name)):
                return (str(self.resume_path), "resume") if self.resume_path else (None, "")
            return None, ""
        if f.kind in TEXT_KINDS and (_COVER.search(label) or _WHY.search(label)):
            text = self._write("Cover letter" if _COVER.search(label) else f.label)
            return (text, "ai_letter") if text else (None, "")
        if f.kind in TEXT_KINDS and (_FIRST.match(label) or _LAST.match(label) or (_FULL.match(label) and f.kind != "textarea")):
            full, how = self.resolve("Full name", [], f.required)
            if not full:
                return None, how
            first, _, last = full.strip().partition(" ")
            return (first if _FIRST.match(label) else last if _LAST.match(label) else full), how
        if f.kind == "radio" and f.options and _RESUME.search(label):  # a board's "choose a saved resume": keep the first
            return f.options[0], "resume"
        options = ["Yes", "No"] if f.kind == "checkbox" and not f.multi else f.options
        return self.resolve(f.label, options, f.required)

    def fill(self, page: Page, fields: list[FormField]) -> FillResult:
        result = FillResult()
        for f in fields:
            if not f.label:
                continue
            value, how = self.decide(f)
            if value is not None and self._put(page, f, value):
                shown = FILE_LABELS.get(how, "A file") if f.kind == "file" else value[:MAX_LOGGED]
                result.answers.append({"question": f.label, "answer": shown, "how": how})
            elif f.required:
                result.missing.append(f.label)
        return result

    def _write(self, question: str) -> str:
        if not self.write_for_job:
            return ""
        if question not in self._written:
            self._written[question] = self.write_for_job(question)
            if question == "Cover letter":
                self.cover_letter = self._written[question]
        return self._written[question]

    @staticmethod
    def _put(page: Page, f: FormField, value: str) -> bool:
        """Put the value in the field; False when it doesn't fit (e.g. not one of the options)."""
        target = page.locator(f.selector)
        try:
            if f.kind in TEXT_KINDS:
                target.first.fill(value)
                if f.combobox:  # type-to-search: take the first suggestion
                    page.wait_for_timeout(600)
                    target.first.press("Enter")
            elif f.kind == "select":
                option = pick(f.options, value)
                if option is None:
                    return False
                target.first.select_option(label=option)
            elif f.kind == "file":
                target.first.set_input_files(value)
            elif f.kind in ("radio", "checkbox") and f.options:
                wanted = [pick(f.options, part) for part in (value.split(",") if f.multi else [value])]
                if not any(wanted):
                    return False
                for box in target.all():
                    if box.get_attribute("data-ja-option") in wanted:
                        box.check(force=True)
            elif f.kind == "checkbox":
                if _is_yes(value):
                    target.first.check(force=True)
            else:
                return False
        except Exception as error:  # a field that can't be filled is treated as unanswered
            log.warning("Couldn't fill %r: %s", f.label, error)
            return False
        return True
