"""Registry of available job-board scrapers. Add new boards here (order = report order)."""

from job_search.scrapers.base import BaseScraper
from job_search.scrapers.indeed import IndeedScraper
from job_search.scrapers.linkedin import LinkedInScraper
from job_search.scrapers.naukri import NaukriScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    LinkedInScraper.name: LinkedInScraper,
    NaukriScraper.name: NaukriScraper,
    IndeedScraper.name: IndeedScraper,
}

__all__ = ["SCRAPERS", "BaseScraper"]
