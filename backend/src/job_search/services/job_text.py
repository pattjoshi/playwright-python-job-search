"""Job descriptions cut down to what matters for scoring, so the AI reads (and bills) less filler."""

import re

# Sections about the company rather than the job: skipped until the next heading.
_FILLER_HEADINGS = re.compile(
    r"^(about (us|the company|the team|the organi[sz]ation|company)|who we are|our (story|culture|mission|values)|"
    r"(perks|benefits)( and perks| & perks)?|what we offer|why (join|work)|life at|equal (employment )?opportunity|"
    r"how to apply|disclaimer|company (overview|description|profile))\b",
    re.IGNORECASE,
)
# Sections about the job itself: reading resumes after a filler section.
_JOB_HEADINGS = re.compile(
    r"^(role|job|position|responsibilit|requirement|qualification|skill|experience|what you|you will|you'll|"
    r"must have|nice to have|preferred|key |duties|tech stack|education|who you are|about the (role|job|position))",
    re.IGNORECASE,
)
# Lines that are filler wherever they appear.
_FILLER_LINES = re.compile(
    r"equal opportunity|does not discriminate|without regard to (race|gender)|reasonable accommodation|"
    r"apply now|click (here|apply)|share your (cv|resume)|send your (cv|resume)|follow us on|visit our website|"
    r"recruitment fraud|never ask(s)? for (money|payment)",
    re.IGNORECASE,
)


def _is_heading(line: str) -> bool:
    return len(line) <= 60 and (line.endswith(":") or len(line.split()) <= 5)


def _filler_heading(line: str) -> bool:
    if _JOB_HEADINGS.match(line):
        return False
    # "About Acme" / "About Acme Technologies:" too, but not "About 3 years of Python" inside the requirements.
    named_about = (line.lower().startswith("about ") and not re.search(r"\d", line)
                   and (line.endswith(":") or len(line.split()) <= 3))
    return bool(_FILLER_HEADINGS.match(line)) or named_about


def clean_description(text: str, limit: int) -> str:
    """The job-relevant part of a description, at most `limit` characters (cut at a word)."""
    kept: list[str] = []
    skipping = False
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        if _is_heading(line):
            if _filler_heading(line):
                skipping = True
                continue
            if _JOB_HEADINGS.match(line):
                skipping = False
        if skipping or _FILLER_LINES.search(line) or (kept and line == kept[-1]):
            continue
        kept.append(line)
    cleaned = "\n".join(kept)
    if len(cleaned) < min(300, len(text) * 0.3):
        # No job heading after the company intro: better to send too much than to lose the job itself.
        cleaned = "\n".join(" ".join(line.split()) for line in text.splitlines()
                             if line.strip() and not _FILLER_LINES.search(line))
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit + 1].rsplit(" ", 1)[0][:limit]
