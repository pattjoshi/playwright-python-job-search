"""Saved search filters (every search uses them): hidden companies."""

from fastapi import APIRouter, Request

from job_search.api.auth import current_user
from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.services.search_filters import FilterError


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise ApiError("Send the filters as JSON.")
    return body


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter(prefix="/api/search-filters")
    service = ctx.search_filters

    def run(action):
        try:
            return action()
        except FilterError as error:
            raise ApiError(error.message) from None

    @router.get("")
    def get(request: Request):
        current_user(request)
        return {"filters": service.get()}

    @router.put("")
    async def save(request: Request):
        current_user(request)
        body = await _body(request)
        return {"filters": run(lambda: service.save(body))}

    @router.post("/hide-company")
    async def hide_company(request: Request):
        current_user(request)
        body = await _body(request)
        return {"filters": run(lambda: service.hide_company(body.get("company", "")))}

    @router.post("/show-company")
    async def show_company(request: Request):
        current_user(request)
        body = await _body(request)
        return {"filters": run(lambda: service.show_company(str(body.get("company", ""))))}

    return router
