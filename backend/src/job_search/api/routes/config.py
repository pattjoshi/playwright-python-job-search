"""What the page needs to render its form: sites, defaults, location choices."""

from fastapi import APIRouter

from job_search import __version__
from job_search.api.dependencies import ApiContext
from job_search.config import LOCATION_CHOICES
from job_search.services.reporting import SITE_NAMES
from job_search.services.resume_service import SUPPORTED_SUFFIXES
from job_search.services.scraping import SCRAPERS


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    @router.get("/api/config")
    def config():
        settings = ctx.settings
        return {
            "sites": [
                {
                    "id": site,
                    "name": SITE_NAMES.get(site, site.title()),
                    "results": settings.results_per_site.get(site, settings.results),
                }
                for site in SCRAPERS
            ],
            "enabled_sites": settings.sites or list(SCRAPERS),
            "location_choices": LOCATION_CHOICES,
            "defaults": {
                "locations": settings.locations,
                "keywords": settings.keywords,
                "hours": settings.hours,
                "experience": list(settings.experience) if settings.experience else None,
                "only_new": settings.only_new,
                "max_pages": settings.max_pages,
                "top": settings.top,
                "parallel_sites": settings.parallel_sites,
            },
            "has_api_key": bool(settings.openai_api_key),
            "running_job": ctx.manager.running.id if ctx.manager.running else None,
            "resume_types": list(SUPPORTED_SUFFIXES),
            "history": ctx.history.counts(),
            "version": __version__,
        }

    return router
