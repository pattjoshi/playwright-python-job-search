"""One router per resource. Each module's build_router(ctx) returns a FastAPI APIRouter."""

from job_search.api.routes import config, history, reports, resume, schedule, search, session

ROUTERS = [module.build_router for module in (resume, session, search, history, schedule, config, reports)]

__all__ = ["ROUTERS"]
