"""The FastAPI application: the API the web page calls, plus the built Next.js page itself.

It only listens on your own computer (127.0.0.1), never on the network.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from job_search.api.dependencies import ApiContext
from job_search.api.routes import ROUTERS
from job_search.config import FRONTEND_BUILD_DIR, OUTPUT_DIR, UPLOAD_DIR, Settings, load_settings
from job_search.models import Profile
from job_search.repositories import CacheRepository, JobHistoryRepository, SessionRepository, resume_key
from job_search.schemas.common import ApiError
from job_search.services.cleanup_service import cleanup
from job_search.services.llm_service import JobMatcherLLM
from job_search.services.resume_service import read_resume_text
from job_search.services.schedule_service import SystemScheduler
from job_search.services.search import run
from job_search.services.search_manager import SearchManager

log = logging.getLogger(__name__)

FRONTEND_MISSING = """<!doctype html><meta charset="utf-8"><title>Job Search</title>
<body style="font-family:system-ui;max-width:640px;margin:60px auto;padding:0 16px;line-height:1.5">
<h1>The web page isn't built yet</h1>
<p>Build it once (needs <a href="https://nodejs.org/">Node.js</a> 20 or newer), then reload this page:</p>
<pre style="background:#f3f4f6;padding:12px;border-radius:8px">cd frontend
npm install
npm run build</pre>
<p>Or double-click <b>start_ui.bat</b> on Windows, which does this for you.</p></body>"""


def default_analyzer(settings: Settings):
    def analyze(resume_path: Path) -> Profile:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file and restart the app.")
        # The same resume file (by content) is only sent to the AI once.
        cache = CacheRepository(settings.cache_path)
        key = resume_key(resume_path, settings.openai_model)
        profile = cache.get_profile(key)
        if profile is None:
            text = read_resume_text(resume_path)
            profile = JobMatcherLLM(settings.openai_api_key, settings.openai_model).extract_profile(text)
            cache.save_profile(key, profile)
        return profile

    return analyze


def create_app(
    settings: Settings | None = None,
    output_dir: Path = OUTPUT_DIR,
    upload_dir: Path = UPLOAD_DIR,
    runner=run,
    analyzer=None,
    system_scheduler: SystemScheduler | None = None,
    frontend_dir: Path = FRONTEND_BUILD_DIR,
) -> FastAPI:
    settings = settings or load_settings()
    data_dir = settings.history_path.parent
    try:
        cleanup(settings.keep_days, data_dir, upload_dir, output_dir, settings.cache_path)
    except Exception:  # housekeeping must never stop the app from starting
        log.exception("Cleanup failed")
    session = SessionRepository(data_dir)
    ctx = ApiContext(
        settings=settings,
        output_dir=output_dir,
        upload_dir=upload_dir,
        data_dir=data_dir,
        manager=SearchManager(settings, output_dir, runner, session),
        history=JobHistoryRepository(settings.history_path),
        session=session,
        scheduler=system_scheduler or SystemScheduler(data_dir),
        analyzer=analyzer or default_analyzer(settings),
    )
    saved = session.resume()
    if saved:  # the resume from before a restart still works without uploading it again
        ctx.resumes[saved["resume_id"]] = {"path": saved["path"], "name": saved["file_name"], "profile": saved["profile"]}

    app = FastAPI(title="Job Search")

    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError):
        return JSONResponse({"error": exc.message}, status_code=exc.status)

    for build_router in ROUTERS:
        app.include_router(build_router(ctx))
    _serve_frontend(app, frontend_dir)
    return app


def _serve_frontend(app: FastAPI, frontend_dir: Path) -> None:
    """Serve the built page at "/" (mounted last, so the API routes above take priority)."""
    if (frontend_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
        return
    log.warning("The web page isn't built yet: run `npm install` and `npm run build` in the frontend folder")

    @app.get("/", response_class=HTMLResponse)
    def frontend_missing():
        return FRONTEND_MISSING
