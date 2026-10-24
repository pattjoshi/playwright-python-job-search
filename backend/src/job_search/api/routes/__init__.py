"""One router per resource. Each module's build_router(ctx) returns a FastAPI APIRouter."""

from job_search.api.routes import (
    answers,
    applications,
    auth,
    auto_apply,
    config,
    extension,
    history,
    notes,
    reports,
    resume,
    schedule,
    search,
    session,
)

ROUTERS = [
    module.build_router
    for module in (auth, applications, answers, auto_apply, extension, notes, resume, session, search, history, schedule, config, reports)
]

__all__ = ["ROUTERS"]
