"""Registry of available job-board scrapers. Add new boards here (order = report order)."""

from job_search.services.scraping.base import BaseScraper
from job_search.services.scraping.browser import SiteSession, block_assets
from job_search.services.scraping.indeed import IndeedScraper
from job_search.services.scraping.linkedin import LinkedInScraper
from job_search.services.scraping.naukri import NaukriScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    LinkedInScraper.name: LinkedInScraper,
    NaukriScraper.name: NaukriScraper,
    IndeedScraper.name: IndeedScraper,
}

__all__ = ["SCRAPERS", "BaseScraper", "SiteSession", "block_assets"]
