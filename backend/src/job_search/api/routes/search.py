"""Start, poll and stop a search."""

from fastapi import APIRouter, HTTPException, Request

from job_search.api.dependencies import ApiContext
from job_search.models import SearchOptions
from job_search.schemas.common import ApiError, int_in_range, str_list
from job_search.services.reporting import SITE_NAMES
from job_search.services.scraping import SCRAPERS

MAX_RESULTS = 100


def build_search_options(ctx: ApiContext, body: dict, resume: dict) -> tuple[SearchOptions, list[str]]:
    """Turn a POST /api/search (or /api/schedule) body into SearchOptions. Raises ApiError."""
    site_counts = body.get("sites")
    if not isinstance(site_counts, dict) or not site_counts:
        raise ApiError("Pick at least one job site.")
    results_per_site = {}
    for site, count in site_counts.items():
        if site not in SCRAPERS:
            raise ApiError(f"Unknown job site: {site}")
        name = SITE_NAMES.get(site, site)
        results_per_site[site] = int_in_range(count, f"Jobs to show for {name}", 1, MAX_RESULTS)
    sites = [site for site in SCRAPERS if site in results_per_site]

    experience = body.get("experience")
    if experience is not None:
        if not (isinstance(experience, list) and len(experience) == 2):
            raise ApiError("Experience must be a 'from' and a 'to' number of years.")
        low = int_in_range(experience[0], "Experience from", 0, 50)
        high = int_in_range(experience[1], "Experience to", 0, 50)
        if low > high:
            raise ApiError("Experience 'from' can't be more than 'to'.")
        experience = (low, high)

    settings = ctx.settings
    return (
        SearchOptions(
            resume_path=resume["path"],
            sites=sites,
            locations=str_list(body.get("locations"), "locations", max_items=10),
            keywords=str_list(body.get("keywords"), "keywords", max_items=8),
            experience=experience,
            max_age_hours=int_in_range(body.get("hours", settings.hours), "Posted within (hours)", 1, 24 * 30),
            max_pages=int_in_range(body.get("max_pages", settings.max_pages), "Pages per search", 1, 10),
            top_n=int_in_range(body.get("top", settings.top), "Jobs to score per site", 5, 200),
            results=settings.results,
            results_per_site=results_per_site,
            only_new=bool(body.get("only_new", False)),
            history_path=settings.history_path,
            cache_path=settings.cache_path,
            parallel_sites=settings.parallel_sites,
            origin="web",
            profile=resume["profile"],
            use_llm=True,
            headless=not body.get("show_browser", True),
            output_dir=ctx.output_dir,
        ),
        sites,
    )


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    def get_job(job_id: str):
        job = ctx.manager.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404)
        return job

    @router.post("/api/search", status_code=202)
    async def start_search(request: Request):
        if not ctx.settings.openai_api_key:
            raise ApiError("OPENAI_API_KEY is not set. Add it to your .env file and restart the app.")
        try:
            body = await request.json()
        except Exception:
            body = None
        if not isinstance(body, dict):
            raise ApiError("Send the search settings as JSON.")
        resume = ctx.resumes.get(str(body.get("resume_id", "")))
        if resume is None:
            raise ApiError("Upload your resume first (or again, if the app was restarted).")

        options, sites = build_search_options(ctx, body, resume)
        try:
            job = ctx.manager.start(options, sites)
        except RuntimeError as error:
            raise ApiError(str(error), status=409) from error
        return {"id": job.id}

    @router.get("/api/search/{job_id}")
    def search_status(job_id: str):
        return get_job(job_id).to_dict()

    @router.post("/api/search/{job_id}/stop")
    def stop_search(job_id: str):
        job = get_job(job_id)
        ctx.manager.stop(job)
        return job.to_dict()

    return router
