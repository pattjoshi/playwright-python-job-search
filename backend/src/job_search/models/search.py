"""What a search was asked to do, how it went, and what it produced."""

from dataclasses import dataclass, field
from pathlib import Path

from job_search.models.job import Job
from job_search.models.profile import Profile
from job_search.models.token_usage import TokenUsage


@dataclass
class SearchOptions:
    resume_path: Path
    sites: list[str] = field(default_factory=list)  # empty = every registered site
    locations: list[str] = field(default_factory=list)  # empty = from the resume; may include "Remote"
    keywords: list[str] = field(default_factory=list)
    experience: tuple[int, int] | None = None  # wanted years, e.g. (1, 2)
    max_age_hours: int = 24
    max_pages: int = 3
    top_n: int = 40  # jobs per site to open and score
    results: int = 10  # jobs per site shown in the report...
    results_per_site: dict[str, int] = field(default_factory=dict)  # ...unless set for that site here
    only_new: bool = False  # hide jobs shown in earlier searches
    history_path: Path | None = None  # where seen/applied/hidden jobs and runs are remembered; None = don't
    cache_path: Path | None = None  # saved descriptions/scores/resume readings; None = no cache
    block_assets: bool = True  # skip images/fonts (and styles when the browser is hidden)
    parallel_sites: bool = True  # search the job sites at the same time (one browser each)
    profile: Profile | None = None  # already-extracted resume profile (skips that AI call)
    origin: str = "cli"  # who started the run (web / daily / cli), for the run history
    use_llm: bool = True
    headless: bool = True
    output_dir: Path = Path("output")


@dataclass
class RunStats:
    """How a run went: shown in the UI and saved in the run history."""

    duration_s: float = 0.0
    sites: dict[str, dict] = field(default_factory=dict)  # site -> {"status", "found"}
    funnel: list = field(default_factory=list)  # [(label, count), ...]
    profile_reused: bool = False
    descriptions_reused: int = 0
    descriptions_fetched: int = 0
    scores_reused: int = 0
    scored: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float | None = None


@dataclass
class SearchResult:
    profile: Profile
    jobs: list[Job]  # every scored job, best first
    top_by_site: dict[str, list[Job]]  # what the HTML report shows
    html_path: Path
    xlsx_path: Path
    csv_path: Path
    stats: RunStats = field(default_factory=RunStats)
