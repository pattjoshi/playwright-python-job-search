"""Answer Bank rules: valid answers, the starter set, and finding the answer for a form question.

How a form question is answered (resolve):
  1. a wording you already have (exact, ignoring case and punctuation)  -> your saved answer
  2. the AI recognises it as one of your questions, reworded            -> that answer (and the wording is remembered)
  3. the AI can answer it from your resume and saved answers            -> a draft, added as "needs review"
  4. otherwise                                                           -> added as "needs answer" for you to write
"""

import logging
from collections.abc import Callable

from job_search.repositories.answer_repository import AnswerRepository
from job_search.services.answers.ai import AnswerAI
from job_search.services.answers.matching import guess_kind, normalize, shortlist
from job_search.services.answers.starters import STARTER_QUESTIONS

log = logging.getLogger(__name__)

CATEGORIES = ("personal", "experience", "compensation", "availability", "work_authorization", "other")
KINDS = ("text", "number", "yes_no", "choice")
ANSWER_STATUSES = ("answered", "needs_review", "needs_answer")
MATCH_LIMIT = 80  # saved questions shown to the AI at most
_LIMITS = {"question": 500, "answer": 5000, "asked_by": 300}


class AnswerError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def _texts(value, name: str, most: int, limit: int) -> list[str]:
    if not isinstance(value, list) or len(value) > most:
        raise AnswerError(f"{name} must be a list of at most {most} items.")
    texts = [str(item).strip()[:limit] for item in value]
    return list(dict.fromkeys(text for text in texts if text))


def clean(fields: dict, creating: bool) -> tuple[dict, list[str] | None]:
    """(validated fields, other wordings or None). Raises AnswerError with a friendly message."""
    cleaned: dict = {}
    for name, limit in _LIMITS.items():
        if name in fields:
            text = str(fields[name] or "").strip()
            if len(text) > limit:
                raise AnswerError(f"{name.replace('_', ' ').capitalize()} is too long (at most {limit} characters).")
            cleaned[name] = text
    if (creating or "question" in cleaned) and not normalize(cleaned.get("question", "")):
        raise AnswerError("Question is required.")
    if "category" in fields:
        if fields["category"] not in CATEGORIES:
            raise AnswerError(f"Category must be one of: {', '.join(CATEGORIES)}.")
        cleaned["category"] = fields["category"]
    if "kind" in fields:
        if fields["kind"] not in KINDS:
            raise AnswerError(f"Type must be one of: {', '.join(KINDS)}.")
        cleaned["kind"] = fields["kind"]
    if "options" in fields:
        cleaned["options"] = _texts(fields["options"], "Options", 30, 200)
    wordings = _texts(fields["wordings"], "Other wordings", 20, 500) if "wordings" in fields else None
    return cleaned, wordings


def _keyed(texts: list[str]) -> list[tuple[str, str]]:
    return [(normalize(text), text) for text in texts if normalize(text)]


class AnswerService:
    def __init__(
        self,
        repo: AnswerRepository,
        ai_factory: Callable[[], AnswerAI | None] = lambda: None,
        resume_text: Callable[[], str | None] = lambda: None,
    ):
        self.repo, self._ai_factory, self._resume_text = repo, ai_factory, resume_text

    def create(self, user_id: int, fields: dict) -> dict:
        cleaned, wordings = clean(fields, creating=True)
        self._check_unique(user_id, cleaned["question"])
        cleaned["status"] = "answered" if cleaned.get("answer") else "needs_answer"
        cleaned["source"] = "you"
        return self.repo.create(user_id, cleaned, _keyed([cleaned["question"], *(wordings or [])]))

    def update(self, user_id: int, answer_id: int, fields: dict) -> dict:
        current = self._get(user_id, answer_id)
        cleaned, wordings = clean(fields, creating=False)
        if "answer" in cleaned:  # you wrote or edited it: that's your answer now
            cleaned["status"] = "answered" if cleaned["answer"] else "needs_answer"
        question = cleaned.get("question", current["question"])
        renamed = question != current["question"]
        if renamed:
            self._check_unique(user_id, question, answer_id)
        if renamed and wordings is None:  # keep the old question as another wording
            wordings = [current["question"], *current["wordings"]]
        keyed = None if wordings is None else _keyed([question, *wordings])
        return self.repo.update(user_id, answer_id, cleaned, keyed)

    def approve(self, user_id: int, answer_id: int) -> dict:
        if not self._get(user_id, answer_id)["answer"]:
            raise AnswerError("Write an answer first.")
        return self.repo.update(user_id, answer_id, {"status": "answered"})

    def add_starters(self, user_id: int) -> int:
        """Add the common questions you don't have yet; returns how many were added."""
        added = 0
        for starter in STARTER_QUESTIONS:
            if self.repo.find_by_key(user_id, normalize(starter["question"])):
                continue
            fields = {"question": starter["question"], "category": starter["category"], "kind": starter.get("kind", "text"),
                      "status": "needs_answer", "source": "starter"}
            self.repo.create(user_id, fields, _keyed([starter["question"], *starter["wordings"]]))
            added += 1
        return added

    def fill_from_resume(self, user_id: int) -> int:
        """Let the AI answer unanswered questions from the resume; the answers wait for your review."""
        ai, resume = self._require_ai(), self._resume()
        if not resume:
            raise AnswerError("Upload your resume on the Search jobs page first.")
        empty = self.repo.for_user(user_id, status="needs_answer")
        if not empty:
            return 0
        kinds = {item["id"]: item["kind"] for item in empty}
        filled = 0
        for answer_id, answer in ai.fill(empty, resume).items():
            if kinds[answer_id] == "yes_no":
                if answer.lower() not in ("yes", "no"):
                    continue
                answer = answer.capitalize()
            self.repo.update(user_id, answer_id, {"answer": answer, "status": "needs_review", "source": "resume"})
            filled += 1
        return filled

    def resolve(self, user_id: int, question: str, options: list[str] | None = None, asked_by: str = "") -> dict:
        """Find (or draft, or add) the answer to a form question.

        Returns {"how": saved|matched|drafted|new, "answer": text to put in the form or None, "entry": the bank entry}.
        A draft is used right away (and waits for your review); a "needs answer" question gives None.
        """
        question = str(question or "").strip()[:_LIMITS["question"]]
        options = _texts(options or [], "Options", 30, 200)
        key = normalize(question)
        if not key:
            raise AnswerError("Question is required.")
        entry, how, ai = self.repo.find_by_key(user_id, key), "saved", self._ai()
        if entry is None and ai:
            bank = self.repo.for_user(user_id)
            match_id = ai.match(question, shortlist(question, bank, MATCH_LIMIT)) if bank else None
            if match_id:
                self.repo.add_wording(user_id, match_id, key, question)
                entry, how = self.repo.get(user_id, match_id), "matched"
        if entry is None:
            entry, how = self._add_from_form(user_id, question, options, asked_by[:_LIMITS["asked_by"]], ai)
        usable = entry["status"] != "needs_answer" and bool(entry["answer"])
        if usable:
            self.repo.mark_used(entry["id"])
        return {"how": how, "answer": entry["answer"] if usable else None, "entry": entry}

    def _add_from_form(self, user_id: int, question: str, options: list[str], asked_by: str, ai: AnswerAI | None):
        fields = {"question": question, "kind": guess_kind(options), "options": options, "asked_by": asked_by,
                  "category": "other", "status": "needs_answer", "source": "form"}
        resume = self._resume() if ai else None
        if ai and resume:
            facts = [{"question": a["question"], "answer": a["answer"]}
                     for a in self.repo.for_user(user_id, status="answered")]
            draft = ai.draft(question, options, resume, facts)
            if draft["category"] in CATEGORIES:
                fields["category"] = draft["category"]
            if draft["found"]:
                fields.update(answer=draft["answer"], status="needs_review", source="ai_draft")
                return self.repo.create(user_id, fields, _keyed([question])), "drafted"
        return self.repo.create(user_id, fields, _keyed([question])), "new"

    def _get(self, user_id: int, answer_id: int) -> dict:
        current = self.repo.get(user_id, answer_id)
        if current is None:
            raise AnswerError("That question isn't in your Answer Bank.", status=404)
        return current

    def _check_unique(self, user_id: int, question: str, answer_id: int | None = None) -> None:
        existing = self.repo.find_by_key(user_id, normalize(question))
        if existing and existing["id"] != answer_id:
            raise AnswerError(f"That question is already in your Answer Bank as “{existing['question']}”.", status=409)

    def _ai(self) -> AnswerAI | None:
        try:
            return self._ai_factory()
        except Exception:  # no key, bad settings: the bank still works without the AI
            log.exception("Answer Bank AI unavailable")
            return None

    def _require_ai(self) -> AnswerAI:
        ai = self._ai()
        if ai is None:
            raise AnswerError("Add your OPENAI_API_KEY to .env and restart the app to use the AI.")
        return ai

    def _resume(self) -> str | None:
        try:
            return self._resume_text()
        except Exception:  # the saved resume file was removed or can't be read
            log.warning("Could not read the saved resume", exc_info=True)
            return None
