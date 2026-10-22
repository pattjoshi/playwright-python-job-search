"""Daily search: save, read and remove the schedule."""

from pathlib import Path

from fastapi import APIRouter, Request

from job_search.api.dependencies import ApiContext
from job_search.api.routes.search import build_search_options
from job_search.models import Schedule, parse_time
from job_search.repositories import delete_schedule, load_schedule, load_state, save_schedule
from job_search.schemas.common import ApiError
from job_search.services.schedule_service import ScheduleError, clean_days, options_to_dict


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    def schedule_status() -> dict:
        schedule = load_schedule(ctx.data_dir)
        state = load_state(ctx.data_dir)
        if state and state.get("report"):
            try:
                relative = Path(state["report"]).resolve().relative_to(ctx.output_dir.resolve())
                state["report_url"] = f"/reports/{relative.as_posix()}"
            except ValueError:
                pass
        summary = None
        if schedule:
            search = schedule.search
            summary = {
                "time": schedule.time,
                "days": schedule.days,
                "open_report": schedule.open_report,
                "next_run": schedule.next_run().isoformat(timespec="minutes"),
                "sites": search.get("results_per_site", {}),
                "keywords": search.get("keywords", []),
                "locations": search.get("locations", []),
                "experience": search.get("experience"),
                "hours": search.get("max_age_hours"),
                "resume": Path(search.get("resume_path", "")).name,
                "saved_at": schedule.saved_at,
            }
        return {
            "supported": ctx.scheduler.kind != "unsupported",
            "kind": ctx.scheduler.kind,
            "schedule": summary,
            "last_run": state,
        }

    @router.get("/api/schedule")
    def get_schedule():
        return schedule_status()

    @router.post("/api/schedule")
    async def set_schedule(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = None
        if not isinstance(body, dict):
            raise ApiError("Send the schedule as JSON.")
        resume = ctx.resumes.get(str(body.get("resume_id", "")))
        if resume is None:
            raise ApiError("Upload your resume first (or again, if the app was restarted).")

        try:
            parse_time(str(body.get("time", "")))
            options, _sites = build_search_options(ctx, body, resume)
            schedule = Schedule(
                time=str(body["time"]).strip(),
                days=clean_days(body.get("days")),
                open_report=bool(body.get("open_report", True)),
                search=options_to_dict(options),
            )
        except ValueError as error:
            raise ApiError(str(error)) from error
        try:
            ctx.scheduler.install(schedule)
        except ScheduleError as error:
            raise ApiError(f"Couldn't set up the daily search: {error}", status=500) from error
        save_schedule(ctx.data_dir, schedule)
        return schedule_status()

    @router.delete("/api/schedule")
    def remove_schedule():
        try:
            ctx.scheduler.remove()
        except ScheduleError as error:
            raise ApiError(f"Couldn't remove the daily search: {error}", status=500) from error
        delete_schedule(ctx.data_dir)
        return schedule_status()

    return router
