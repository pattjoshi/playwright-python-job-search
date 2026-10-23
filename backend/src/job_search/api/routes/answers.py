"""Answer Bank: list, add, edit, approve and delete answers; the starter set; fill from resume; try a question."""

from fastapi import APIRouter, Request

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.services.answers import ANSWER_STATUSES, CATEGORIES, AnswerError


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise ApiError("Send the answer as JSON.")
    return body


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/answers")
    service = ctx.answers

    def run(action):
        try:
            return action()
        except AnswerError as error:
            raise ApiError(error.message, status=error.status) from None

    @router.get("")
    def list_answers(request: Request, status: str = "", category: str = "", q: str = ""):
        if status and status not in ANSWER_STATUSES:
            raise ApiError(f"status must be one of {', '.join(ANSWER_STATUSES)}")
        if category and category not in CATEGORIES:
            raise ApiError(f"category must be one of {', '.join(CATEGORIES)}")
        user_id = current_user(request).id
        return {"answers": service.repo.for_user(user_id, status, category, q.strip()[:100]), "counts": service.repo.counts(user_id)}

    @router.post("")
    async def add_answer(request: Request):
        user, body = current_user(request), await _body(request)
        return {"answer": run(lambda: service.create(user.id, body))}

    @router.post("/starters")
    def add_starters(request: Request):
        return {"added": service.add_starters(current_user(request).id)}

    @router.post("/fill-from-resume")
    def fill_from_resume(request: Request):
        return {"filled": run(lambda: service.fill_from_resume(current_user(request).id))}

    @router.post("/try")
    async def try_question(request: Request):
        """Answer a question the way auto-apply will: saved, matched, drafted or added for you to answer."""
        user, body = current_user(request), await _body(request)
        options = body.get("options") or []
        return run(lambda: service.resolve(user.id, body.get("question", ""), options, str(body.get("asked_by") or "")))

    @router.patch("/{answer_id}")
    async def edit_answer(request: Request, answer_id: int):
        user, body = current_user(request), await _body(request)
        return {"answer": run(lambda: service.update(user.id, answer_id, body))}

    @router.post("/{answer_id}/approve")
    def approve(request: Request, answer_id: int):
        return {"answer": run(lambda: service.approve(current_user(request).id, answer_id))}

    @router.delete("/{answer_id}")
    def delete_answer(request: Request, answer_id: int):
        if not service.repo.delete(current_user(request).id, answer_id):
            raise ApiError("That question isn't in your Answer Bank.", status=404)
        return {"ok": True}

    return router
