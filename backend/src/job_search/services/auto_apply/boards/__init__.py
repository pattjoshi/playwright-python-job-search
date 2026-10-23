"""Easy Apply on the job boards themselves (Naukri, LinkedIn, Indeed), with your own logins."""

from job_search.services.auto_apply.boards.base import Board
from job_search.services.auto_apply.boards.indeed import IndeedBoard
from job_search.services.auto_apply.boards.linkedin import LinkedInBoard
from job_search.services.auto_apply.boards.naukri import NaukriBoard

BOARDS: dict[str, type[Board]] = {"naukri": NaukriBoard, "linkedin": LinkedInBoard, "indeed": IndeedBoard}

__all__ = ["BOARDS", "Board"]
