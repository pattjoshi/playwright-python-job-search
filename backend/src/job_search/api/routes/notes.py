"""Notes: the page tree, and reading, writing, moving and deleting pages (only your own)."""

from fastapi import APIRouter, Request

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.services.notes import NoteError


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise ApiError("Send the page as JSON.")
    return body


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/notes")
    service = ctx.notes

    def run(action):
        try:
            return action()
        except NoteError as error:
            raise ApiError(error.message, status=error.status) from None

    @router.get("")
    def tree(request: Request):
        return {"pages": service.repo.tree(current_user(request).id)}

    @router.post("")
    async def create(request: Request):
        user, body = current_user(request), await _body(request)
        return {"page": run(lambda: service.create(user.id, body))}

    @router.get("/{note_id}")
    def get(request: Request, note_id: int):
        page = service.repo.get(current_user(request).id, note_id)
        if page is None:
            raise ApiError("That page doesn't exist.", status=404)
        return {"page": page}

    @router.patch("/{note_id}")
    async def edit(request: Request, note_id: int):
        user, body = current_user(request), await _body(request)
        return {"page": run(lambda: service.update(user.id, note_id, body))}

    @router.post("/{note_id}/move")
    async def move(request: Request, note_id: int):
        user, body = current_user(request), await _body(request)
        parent_id, position = body.get("parent_id"), body.get("position", 0)
        if (parent_id is not None and not isinstance(parent_id, int)) or not isinstance(position, int):
            raise ApiError("parent_id must be a page id (or null) and position a number.")
        return {"pages": run(lambda: service.move(user.id, note_id, parent_id, position))}

    @router.delete("/{note_id}")
    def remove(request: Request, note_id: int):
        run(lambda: service.delete(current_user(request).id, note_id))
        return {"ok": True}

    return router
