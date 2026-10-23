"""Auto-apply: settings, the queue, run / stop, screenshots, and queueing the last search's matches."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.models import Job
from job_search.schemas.common import ApiError
from job_search.services.auto_apply import AutoApplyError

_JOB_FIELDS = ("source", "job_id", "title", "company", "location", "url", "apply_url", "score")


def _jobs_from_last_search(ctx: ApiContext) -> list[Job]:
    """The jobs on the Search page's last finished search (with their apply links)."""
    last = (ctx.session.load() or {}).get("last_job") or {}
    result = last.get("result") or {}
    jobs = []
    for site in result.get("sites") or []:
        for item in site.get("jobs") or []:
            if isinstance(item, dict) and item.get("job_id"):
                jobs.append(Job(**{name: item.get(name) for name in _JOB_FIELDS if name in item}))
    return jobs


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/auto-apply")
    manager = ctx.auto_apply
    service = manager.service

    def run(action):
        try:
            return action()
        except AutoApplyError as error:
            raise ApiError(error.message, status=error.status) from None

    @router.get("")
    def overview(request: Request):
        return {**service.overview(current_user(request).id), "run": manager.status()}

    @router.put("/settings")
    async def save_settings(request: Request):
        user = current_user(request)
        try:
            body = await request.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise ApiError("Send the settings as JSON.")
        return {"settings": run(lambda: service.save_settings(user.id, body))}

    @router.post("/queue-last-search")
    def queue_last_search(request: Request):
        return {"added": service.queue_jobs(current_user(request).id, _jobs_from_last_search(ctx))}

    @router.post("/run")
    def start(request: Request):
        return {"run": run(lambda: manager.start(current_user(request).id))}

    @router.post("/stop")
    def stop(request: Request):
        current_user(request)
        return {"run": manager.stop()}

    @router.post("/{job_id}/retry")
    def retry(request: Request, job_id: int):
        return {"job": run(lambda: service.retry(current_user(request).id, job_id))}

    @router.delete("/{job_id}")
    def remove(request: Request, job_id: int):
        run(lambda: service.remove(current_user(request).id, job_id))
        return {"ok": True}

    @router.get("/{job_id}/screenshot")
    def screenshot(request: Request, job_id: int):
        path = run(lambda: service.screenshot(current_user(request).id, job_id))
        if path is None:
            raise ApiError("No screenshot for that job.", status=404)
        return FileResponse(path, media_type="image/png")

    return router
