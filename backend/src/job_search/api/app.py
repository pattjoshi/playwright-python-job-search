"""The FastAPI application: the API the web page calls, plus the built Next.js page itself.

It only listens on your own computer (127.0.0.1), never on the network.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from job_search.api.auth import install_auth
from job_search.api.dependencies import ApiContext
from job_search.api.frontend import serve_frontend
from job_search.api.routes import ROUTERS
from job_search.config import FRONTEND_BUILD_DIR, OUTPUT_DIR, UPLOAD_DIR, Settings, load_settings
from job_search.models import Profile
from job_search.repositories import (
    AnswerRepository,
    ApplicationRepository,
    AutoApplyRepository,
    CacheRepository,
    JobHistoryRepository,
    SessionRepository,
    UserRepository,
    resume_key,
)
from job_search.schemas.common import ApiError
from job_search.services.answers import AnswerAI, AnswerService
from job_search.services.applications import ApplicationService
from job_search.services.auth import AuthService
from job_search.services.auto_apply import AutoApplyManager, AutoApplyService, open_browser
from job_search.services.cleanup_service import cleanup
from job_search.services.llm_service import JobMatcherLLM
from job_search.services.resume_service import read_resume_text
from job_search.services.schedule_service import SystemScheduler
from job_search.services.search import run
from job_search.services.search_manager import SearchManager

log = logging.getLogger(__name__)


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


def default_answer_ai(settings: Settings):
    def make() -> AnswerAI | None:
        return AnswerAI(JobMatcherLLM(settings.openai_api_key, settings.openai_model)) if settings.openai_api_key else None

    return make


def saved_resume_text(session: SessionRepository):
    """The text of the resume on the Search page (None when there isn't one)."""
    def read() -> str | None:
        saved = session.resume()
        return read_resume_text(saved["path"]) if saved else None

    return read


def saved_resume_path(session: SessionRepository):
    """The resume file on the Search page (None when there isn't one)."""
    def path() -> Path | None:
        saved = session.resume()
        return saved["path"] if saved else None

    return path


def build_auto_apply(settings: Settings, session: SessionRepository, answer_ai=None, browser=None) -> AutoApplyManager:
    """Auto-apply with the Answer Bank and the tracker it uses (shared by the web app and the daily search)."""
    path = settings.history_path
    answer_ai = answer_ai or default_answer_ai(settings)
    answers = AnswerService(AnswerRepository(path), answer_ai, saved_resume_text(session))
    return AutoApplyManager(AutoApplyService(
        AutoApplyRepository(path), answers, ApplicationService(ApplicationRepository(path)), path.parent / "auto-apply",
        saved_resume_path(session), saved_resume_text(session), answer_ai,
        browser or (lambda headless: open_browser(headless, settings.chromium_executable, path.parent / "browser-profile")),
        board_logins=settings.board_logins,
    ))


def create_app(
    settings: Settings | None = None,
    output_dir: Path = OUTPUT_DIR,
    upload_dir: Path = UPLOAD_DIR,
    runner=run,
    analyzer=None,
    system_scheduler: SystemScheduler | None = None,
    frontend_dir: Path = FRONTEND_BUILD_DIR,
    answer_ai=None,
    auto_apply_browser=None,
) -> FastAPI:
    settings = settings or load_settings()
    data_dir = settings.history_path.parent
    try:
        cleanup(settings.keep_days, data_dir, upload_dir, output_dir, settings.cache_path)
    except Exception:  # housekeeping must never stop the app from starting
        log.exception("Cleanup failed")
    session = SessionRepository(data_dir)
    users = UserRepository(settings.history_path)
    auto_apply = build_auto_apply(settings, session, answer_ai, auto_apply_browser)
    auto_apply.service.repo.requeue_interrupted()
    answers, applications = auto_apply.service.answers, auto_apply.service.applications

    def queue_for_auto_apply(result) -> None:
        owner = users.owner_id()
        if owner is not None:
            auto_apply.after_search(owner, result.jobs)

    ctx = ApiContext(
        settings=settings,
        output_dir=output_dir,
        upload_dir=upload_dir,
        data_dir=data_dir,
        manager=SearchManager(settings, output_dir, runner, session, after_search=queue_for_auto_apply),
        history=JobHistoryRepository(settings.history_path),
        session=session,
        scheduler=system_scheduler or SystemScheduler(data_dir),
        analyzer=analyzer or default_analyzer(settings),
        auth=AuthService(users),
        applications=applications,
        answers=answers,
        auto_apply=auto_apply,
    )
    saved = session.resume()
    if saved:  # the resume from before a restart still works without uploading it again
        ctx.resumes[saved["resume_id"]] = {"path": saved["path"], "name": saved["file_name"], "profile": saved["profile"]}

    app = FastAPI(title="Job Search")

    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError):
        return JSONResponse({"error": exc.message}, status_code=exc.status)

    install_auth(app, ctx.auth)
    for build_router in ROUTERS:
        app.include_router(build_router(ctx))
    serve_frontend(app, frontend_dir)
    return app
