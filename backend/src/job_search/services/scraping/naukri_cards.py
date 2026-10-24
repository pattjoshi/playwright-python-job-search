"""Naukri fallback: read the job cards from the rendered search page when its JSON can't be captured."""

import re

from playwright.sync_api import Page

from job_search.models import Job
from job_search.services.matching_service import parse_relative_age

BASE_URL = "https://www.naukri.com"
CARD = "div.srp-jobtuple-wrapper, article.jobTuple"
TITLE = "a.title"
COMPANY = "a.comp-name, .comp-name"
LOCATION = ".locWdth, .location, .loc"
POSTED = ".job-post-day, .type br + span, .jobTupleFooter span.fleft"
SNIPPET = ".job-desc, .job-description"
EXPERIENCE = ".expwdth, .exp-wrap, .experience"
TAGS = "ul.tags-gt li, ul.tags li"


def parse_search_results(page: Page) -> list[Job]:
    """Fallback: read job cards from the rendered search page."""
    jobs = []
    for card in page.locator(CARD).all():
        link = card.locator(TITLE).first
        if not link.count():
            continue
        title = " ".join(link.inner_text().split())
        url = absolute_url(link.get_attribute("href") or "")
        job_id = card.get_attribute("data-job-id") or _job_id_from_url(url)
        if not (title and job_id):
            continue

        posted_text = _text(card, POSTED)
        tags = [" ".join(tag.inner_text().split()) for tag in card.locator(TAGS).all()]
        description = _text(card, SNIPPET)
        if tags:
            description = f"{description}\nSkills: {', '.join(tags)}".strip()
        jobs.append(
            Job(
                source="naukri",
                job_id=job_id,
                title=title,
                company=_text(card, COMPANY),
                location=_text(card, LOCATION),
                url=url,
                posted_text=posted_text,
                hours_ago=parse_relative_age(posted_text),
                description=description,
                experience=_text(card, EXPERIENCE),
            )
        )
    return jobs


def _job_id_from_url(url: str) -> str:
    match = re.search(r"-(\d{6,})(?:\?|$)", url)
    return match.group(1) if match else ""


def _text(card, selector: str) -> str:
    element = card.locator(selector).first
    return " ".join(element.inner_text().split()) if element.count() else ""


def absolute_url(url: str) -> str:
    return url if url.startswith("http") else f"{BASE_URL}/{url.lstrip('/')}"
