"""Shared request-handling context built once by create_app() and passed to each router."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from job_search.config import Settings
from job_search.models import Profile
from job_search.repositories import JobHistoryRepository, SessionRepository
from job_search.services.applications import ApplicationService
from job_search.services.auth import AuthService
from job_search.services.schedule_service import SystemScheduler
from job_search.services.search_manager import SearchManager


@dataclass
class ApiContext:
    settings: Settings
    output_dir: Path
    upload_dir: Path
    data_dir: Path
    manager: SearchManager
    history: JobHistoryRepository
    session: SessionRepository
    scheduler: SystemScheduler
    analyzer: Callable[[Path], Profile]
    auth: AuthService
    applications: ApplicationService
    resumes: dict[str, dict] = field(default_factory=dict)
