"""The Chrome extension's API (signed in with its key, see api/auth.py): next job, answers, results, resume."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.services.auto_apply import AutoApplyError
from job_search.services.auto_apply.extension_bridge import ExtensionBridge


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise ApiError("Send JSON.")
    return body


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/extension")
    bridge = ExtensionBridge(ctx.auto_apply.service)

    def run(action):
        try:
            return action()
        except AutoApplyError as error:
            raise ApiError(error.message, status=error.status) from None

    @router.get("/status")
    def status(request: Request):
        user = current_user(request)
        return {"user": user.name or user.email, **bridge.status(user.id)}

    @router.post("/next")
    def next_job(request: Request):
        return {"job": bridge.claim_next(current_user(request).id)}

    @router.post("/jobs/{job_id}/answer")
    async def answer(request: Request, job_id: int):
        user, body = current_user(request), await _body(request)
        question = str(body.get("question") or "").strip()
        if not question:
            raise ApiError("question is required.")
        options = body.get("options") if isinstance(body.get("options"), list) else []
        return run(lambda: bridge.answer(user.id, job_id, question, options, bool(body.get("required", True))))

    @router.post("/jobs/{job_id}/write")
    async def write(request: Request, job_id: int):
        user, body = current_user(request), await _body(request)
        return {"text": run(lambda: bridge.write(user.id, job_id, str(body.get("question") or "Cover letter")))}

    @router.post("/jobs/{job_id}/result")
    async def result(request: Request, job_id: int):
        user, body = current_user(request), await _body(request)
        return {"job": run(lambda: bridge.report(user.id, job_id, body))}

    @router.get("/resume")
    def resume(request: Request):
        current_user(request)
        path = ctx.auto_apply.service.resume_path()
        if path is None:
            raise ApiError("Upload your resume on the Search jobs page first.", status=404)
        return FileResponse(path, filename=path.name.split("_", 2)[-1])

    return router
