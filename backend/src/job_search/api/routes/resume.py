"""Upload and read a resume."""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from job_search.api.dependencies import ApiContext
from job_search.schemas.common import ApiError
from job_search.schemas.serializers import resume_to_dict, suggest_experience
from job_search.services.resume_service import SUPPORTED_SUFFIXES, safe_filename

log = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def build_router(ctx: ApiContext) -> APIRouter:
    router = APIRouter()

    @router.post("/api/analyze")
    async def analyze(resume: UploadFile | None = File(None)):
        if resume is None or not resume.filename:
            raise ApiError("Choose your resume file first.")
        suffix = Path(resume.filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise ApiError(f"Resume must be one of: {', '.join(SUPPORTED_SUFFIXES)}")

        data = await resume.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise ApiError(f"Resume file is too big (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).", status=413)

        ctx.upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = safe_filename(resume.filename) or f"resume{suffix}"
        path = ctx.upload_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{safe_name}"
        path.write_bytes(data)
        try:
            profile = ctx.analyzer(path)
        except Exception as error:  # unreadable file, OpenAI error, missing key...
            log.warning("Could not read resume: %s", error)
            raise ApiError(f"Could not read your resume: {error}") from error

        resume_id = uuid.uuid4().hex[:12]
        ctx.resumes[resume_id] = {"path": path, "name": resume.filename, "profile": profile}
        suggested = suggest_experience(profile.years_experience)
        ctx.session.save_resume(resume_id, path, resume.filename, profile, suggested)
        return resume_to_dict(resume_id, resume.filename, profile, suggested)

    return router
