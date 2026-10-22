"""Serves the generated HTML/Excel/CSV reports."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from job_search.api.dependencies import ApiContext


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    @router.get("/reports/{name:path}")
    def report(name: str):
        base = ctx.output_dir.resolve()
        path = (base / name).resolve()
        try:
            path.relative_to(base)  # rejects a name that escapes output_dir (e.g. "../../.env")
        except ValueError:
            raise HTTPException(status_code=404) from None
        if not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path)

    return router
