"""Registry of available job-board scrapers. Add new boards here."""

from job_search.scrapers.base import BaseScraper
from job_search.scrapers.linkedin import LinkedInScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    LinkedInScraper.name: LinkedInScraper,
}

__all__ = ["SCRAPERS", "BaseScraper"]
