"""Serves the built Next.js page (frontend/out) from the same server as the API."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

log = logging.getLogger(__name__)

FRONTEND_MISSING = """<!doctype html><meta charset="utf-8"><title>Job Search</title>
<body style="font-family:system-ui;max-width:640px;margin:60px auto;padding:0 16px;line-height:1.5">
<h1>The web page isn't built yet</h1>
<p>Build it once (needs <a href="https://nodejs.org/">Node.js</a> 20 or newer), then reload this page:</p>
<pre style="background:#f3f4f6;padding:12px;border-radius:8px">cd frontend
npm install
npm run build</pre>
<p>Or double-click <b>start_ui.bat</b> on Windows, which does this for you.</p></body>"""


IMMUTABLE = "public, max-age=31536000, immutable"


class PageFiles(StaticFiles):
    """Static files with clean page URLs: Next.js exports /dashboard as dashboard.html."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await self._get_or_404(path, scope)
        if path.startswith("_next/static/") and response.status_code < 400:
            # Next.js puts a content hash in these file names, so the browser can keep them for good (no re-checks).
            response.headers["Cache-Control"] = IMMUTABLE
        if response.status_code == 404 and path.strip("/") and not Path(path).suffix:
            page = await self._get_or_404(f"{path.strip('/')}.html", scope)
            if page.status_code < 400:  # 200, or 304 "not modified" when the browser reloads
                return page
        return response

    async def _get_or_404(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return Response(status_code=404)


def serve_frontend(app: FastAPI, frontend_dir: Path) -> None:
    """Serve the built page at "/" (mounted last, so the API routes take priority)."""
    if (frontend_dir / "index.html").is_file():
        app.mount("/", PageFiles(directory=frontend_dir, html=True), name="frontend")
        return
    log.warning("The web page isn't built yet: run `npm install` and `npm run build` in the frontend folder")

    @app.get("/", response_class=HTMLResponse)
    def frontend_missing():
        return FRONTEND_MISSING
