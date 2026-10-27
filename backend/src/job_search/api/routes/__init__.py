"""One router per resource. Each module's build_router(ctx) returns a FastAPI APIRouter."""

from job_search.api.routes import (
    applications,
    auth,
    config,
    history,
    notes,
    openai_key,
    reports,
    resume,
    schedule,
    search,
    search_filters,
    session,
)

ROUTERS = [
    module.build_router
    for module in (
        auth, applications, notes, resume, session, search, search_filters, history, schedule,
        config, openai_key, reports,
    )
]

__all__ = ["ROUTERS"]
