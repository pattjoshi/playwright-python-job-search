"""What the page showed before a reload: the resume and the last search."""

from fastapi import APIRouter

from job_search.api.dependencies import ApiContext
from job_search.models import Job
from job_search.schemas.common import ApiError
from job_search.schemas.serializers import resume_to_dict


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    @router.get("/api/session")
    def get_session():
        data = ctx.session.load()
        saved = ctx.session.resume()
        resume = (
            resume_to_dict(saved["resume_id"], saved["file_name"], saved["profile"], saved.get("suggested_experience"))
            if saved
            else None
        )
        last_job = data.get("last_job")
        if last_job and last_job.get("result"):
            # Show jobs you marked applied/hidden since then as such.
            jobs = [
                Job(j["source"], j["job_id"], j.get("title", ""), "", "", "")
                for site in last_job["result"]["sites"]
                for j in site["jobs"]
            ]
            statuses = ctx.history.statuses(jobs)
            for site in last_job["result"]["sites"]:
                for j in site["jobs"]:
                    j["status"] = statuses.get((j["source"], j["job_id"]))
        return {"resume": resume, "last_job": last_job}

    @router.post("/api/session/clear")
    def clear_session():
        if ctx.manager.running:
            raise ApiError("Stop the running search before clearing.", status=409)
        saved = ctx.session.load().get("resume")
        if saved:
            ctx.resumes.pop(saved.get("resume_id"), None)
        ctx.session.clear()
        return {"resume": None, "last_job": None}

    return router
