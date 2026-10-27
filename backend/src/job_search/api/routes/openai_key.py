"""Settings → OpenAI key: see which key is used, save your own (checked with OpenAI first), or remove it."""

from fastapi import APIRouter, Request

from job_search.api.auth import require_owner
from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.services.openai_key import OpenAIKeyError


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/settings/openai-key")

    @router.get("")
    def status():
        return ctx.openai_key.status()  # never the key itself

    @router.put("")
    async def save(request: Request):
        require_owner(request)
        try:
            body = await request.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise ApiError("Send the key as JSON: {\"key\": \"sk-…\"}.")
        try:
            return ctx.openai_key.save(body.get("key"))
        except OpenAIKeyError as error:
            raise ApiError(str(error)) from error

    @router.delete("")
    def remove(request: Request):
        require_owner(request)
        return ctx.openai_key.remove()

    return router
