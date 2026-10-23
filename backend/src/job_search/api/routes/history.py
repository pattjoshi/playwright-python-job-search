"""Applied/hidden/seen jobs, and the run history."""

from pathlib import Path

from fastapi import APIRouter, Request

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.repositories import STATUSES
from job_search.schemas.common import ApiError
from job_search.services.scraping import SCRAPERS


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    @router.post("/api/jobs/status")
    async def set_job_status(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = None
        body = body if isinstance(body, dict) else {}
        source, job_id, status = (str(body.get(key, "")) for key in ("source", "job_id", "status"))
        if source not in SCRAPERS or not job_id or status not in STATUSES:
            raise ApiError(f"Need a known source, a job_id and a status ({', '.join(STATUSES)}).")
        job = {key: str(body.get(key, ""))[:limit] for key, limit in (("title", 300), ("company", 200), ("url", 1000), ("location", 200))}
        ctx.history.set_status(source, job_id, status, title=job["title"], company=job["company"], url=job["url"])
        tracked = False
        if status == "applied":  # also keep it in the application tracker
            _, tracked = ctx.applications.track_job(current_user(request).id, {**job, "source": source, "job_id": job_id}, "applied")
        return {"ok": True, "history": ctx.history.counts(), "tracked": tracked}

    @router.get("/api/history")
    def list_history(status: str = "applied"):
        if status not in STATUSES:
            raise ApiError(f"status must be one of {', '.join(STATUSES)}")
        return {"jobs": ctx.history.list_jobs(status), "history": ctx.history.counts()}

    @router.post("/api/history/forget")
    def forget_history():
        forgotten = ctx.history.forget_seen()
        return {"forgotten": forgotten, "history": ctx.history.counts()}

    @router.get("/api/runs")
    def list_runs():
        runs = ctx.history.list_runs(limit=50)
        for item in runs:
            report = item.get("report")
            item["report_url"] = None
            if report:
                try:
                    relative = Path(report).resolve().relative_to(ctx.output_dir.resolve())
                    if (ctx.output_dir / relative).exists():
                        item["report_url"] = f"/reports/{relative.as_posix()}"
                except ValueError:
                    pass
        return {
            "runs": runs,
            "costs_configured": ctx.settings.price_input is not None and ctx.settings.price_output is not None,
        }

    return router
