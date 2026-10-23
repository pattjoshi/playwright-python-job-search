"""Small text helpers for matching form questions to saved ones without the AI."""

import re

_NOT_WORD = re.compile(r"[^\w\s]+")
_SPACES = re.compile(r"\s+")
_YES_NO = {"yes", "no"}
_STOP_WORDS = {"a", "an", "the", "you", "your", "do", "are", "is", "what", "of", "in", "to", "for", "have", "please"}


def normalize(question: str) -> str:
    """Lower case, no punctuation or required-field stars: "Notice Period *" → "notice period"."""
    return _SPACES.sub(" ", _NOT_WORD.sub(" ", question.lower())).strip()


def guess_kind(options: list[str]) -> str:
    """yes_no when a form offers just Yes/No, choice for other option lists, else free text."""
    if not options:
        return "text"
    return "yes_no" if {normalize(option) for option in options} <= _YES_NO else "choice"


def shortlist(question: str, answers: list[dict], limit: int) -> list[dict]:
    """The saved questions sharing the most words with this one (all of them when the bank is small)."""
    if len(answers) <= limit:
        return answers
    words = set(normalize(question).split()) - _STOP_WORDS

    def overlap(answer: dict) -> int:
        text = " ".join([answer["question"], *answer.get("wordings", [])])
        return len(words & set(normalize(text).split()))

    return sorted(answers, key=overlap, reverse=True)[:limit]
