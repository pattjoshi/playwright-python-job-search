"""Application tracker: list, add, edit, move, delete, timeline and stats (only your own applications)."""

from fastapi import APIRouter, Request

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.services.applications import STATUSES, ApplicationError


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise ApiError("Send the application as JSON.")
    return body


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/applications")
    service = ctx.applications

    def run(action):
        try:
            return action()
        except ApplicationError as error:
            raise ApiError(error.message, status=error.status) from None

    @router.get("")
    def list_applications(request: Request, q: str = "", status: str = ""):
        if status and status not in STATUSES:
            raise ApiError(f"status must be one of {', '.join(STATUSES)}")
        return {"applications": service.repo.for_user(current_user(request).id, q.strip()[:100], status), "statuses": list(STATUSES)}

    @router.post("")
    async def add_application(request: Request):
        user, body = current_user(request), await _body(request)
        return {"application": run(lambda: service.create(user.id, body))}

    @router.get("/stats")
    def stats(request: Request):
        return service.repo.stats(current_user(request).id, service.today())

    @router.post("/track")
    async def track(request: Request):
        """Add a job from the search results (status `saved`, or `applied`)."""
        user, body = current_user(request), await _body(request)
        status = body.get("status", "saved") if body.get("status") in ("saved", "applied") else "saved"
        application, created = run(lambda: service.track_job(user.id, body, status))
        return {"application": application, "created": created}

    @router.post("/import-applied")
    def import_applied(request: Request):
        """Copy the jobs you marked applied in searches into the tracker (once each)."""
        user = current_user(request)
        added = 0
        for job in ctx.history.list_jobs("applied"):
            _, created = run(lambda job=job: service.track_job(user.id, job, "applied"))
            added += created
        return {"added": added}

    @router.get("/{app_id}")
    def get_application(request: Request, app_id: int):
        user = current_user(request)
        application = service.repo.get(user.id, app_id)
        if application is None:
            raise ApiError("That application doesn't exist.", status=404)
        return {"application": application, "events": service.repo.events(user.id, app_id)}

    @router.patch("/{app_id}")
    async def edit_application(request: Request, app_id: int):
        user, body = current_user(request), await _body(request)
        return {"application": run(lambda: service.update(user.id, app_id, body))}

    @router.delete("/{app_id}")
    def delete_application(request: Request, app_id: int):
        if not service.repo.delete(current_user(request).id, app_id):
            raise ApiError("That application doesn't exist.", status=404)
        return {"ok": True}

    return router
