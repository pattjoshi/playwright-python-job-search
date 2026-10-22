"""What we learned about the candidate from their resume."""

from dataclasses import dataclass, field


@dataclass
class Profile:
    current_title: str = ""
    target_titles: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    years_experience: float | None = None
    locations: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    summary: str = ""
