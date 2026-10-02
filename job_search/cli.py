"""Command-line entry point: python -m job_search --resume my_resume.pdf"""

import argparse
import logging
import webbrowser
from pathlib import Path

from openai import OpenAIError

from job_search.config import Settings, load_settings
from job_search.pipeline import SearchOptions, run
from job_search.scrapers import SCRAPERS
from job_search.utils import parse_experience_option


def build_parser() -> argparse.ArgumentParser:
    # Search options default to None so we can tell "not passed" apart and fall back to .env.
    parser = argparse.ArgumentParser(
        prog="job_search",
        description="Find recent jobs that match your resume. Defaults for every search option can be set in .env.",
    )
    parser.add_argument("--resume", type=Path, help="Path to your resume (.pdf, .docx, .txt) [.env: RESUME]")
    parser.add_argument(
        "--sites",
        nargs="+",
        choices=list(SCRAPERS),
        help="Job boards to search (default: all) [.env: SITES]",
    )
    parser.add_argument(
        "--location",
        dest="locations",
        nargs="+",
        help="Where to search, e.g. --location Pune Bengaluru Remote (default: from your resume) [.env: LOCATION]",
    )
    parser.add_argument(
        "--experience", help="Years of experience wanted, e.g. '1-2' or '3' [.env: EXPERIENCE]"
    )
    parser.add_argument(
        "--only-new",
        action=argparse.BooleanOptionalAction,
        help="Only show jobs not shown in earlier searches [.env: ONLY_NEW]",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        help="Override search phrases, e.g. --keywords 'Python Developer' 'SDET' [.env: KEYWORDS]",
    )
    parser.add_argument("--hours", type=int, help="Only jobs posted within this many hours (default 24) [.env: HOURS]")
    parser.add_argument("--max-pages", type=int, help="Result pages per search (default 3) [.env: MAX_PAGES]")
    parser.add_argument(
        "--results",
        nargs="+",
        metavar="N|SITE=N",
        help="Jobs to show per site, best first: '--results 15' for every site, or "
        "'--results linkedin=20 naukri=12' (default 10) [.env: RESULTS, RESULTS_LINKEDIN, ...]",
    )
    parser.add_argument("--top", type=int, help="Jobs per site to open and score (default 40) [.env: TOP]")
    parser.add_argument("--no-llm", action="store_true", help="Skip OpenAI; rank by keyword overlap instead")
    parser.add_argument("--show-browser", action="store_true", help="Watch the browser while it works")
    parser.add_argument("--no-open", action="store_true", help="Don't open the HTML report when finished")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Where to save reports")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug logs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        options = build_options(args, settings)
    except ValueError as error:
        parser.error(str(error))

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep third-party HTTP chatter out of normal output.
    for noisy in ("httpx", "openai", "pdfminer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    try:
        result = run(options, settings)
    except (FileNotFoundError, ValueError) as error:
        logging.error("%s", error)
        return 1
    except OpenAIError as error:
        logging.error("OpenAI request failed: %s", error)
        return 1

    print_summary(result)
    if not args.no_open:
        webbrowser.open(result.html_path.resolve().as_uri())
    return 0


def build_options(args: argparse.Namespace, settings: Settings) -> SearchOptions:
    """Merge command-line options over .env defaults. Raises ValueError for unusable combinations."""

    def pick(cli_value, env_value):
        return env_value if cli_value is None else cli_value

    resume = pick(args.resume, settings.resume)
    if resume is None:
        raise ValueError("no resume given: pass --resume my_resume.pdf, or set RESUME=... in .env")

    sites = pick(args.sites, settings.sites) or list(SCRAPERS)
    unknown = [site for site in sites if site not in SCRAPERS]
    if unknown:
        raise ValueError(f"unknown site(s) {', '.join(unknown)} in SITES; available: {', '.join(SCRAPERS)}")

    keywords = pick(args.keywords, settings.keywords)
    if args.no_llm and not keywords:
        raise ValueError("--no-llm needs keywords (--keywords or KEYWORDS in .env), since there is no AI to read your resume")

    experience = parse_experience_option(args.experience) if args.experience else settings.experience

    results, results_per_site = settings.results, dict(settings.results_per_site)
    if args.results:
        cli_results, cli_per_site = parse_results(args.results)
        if cli_results is not None:
            # A plain number on the command line applies to every site for this run.
            results, results_per_site = cli_results, {}
        results_per_site.update(cli_per_site)
    unknown = [site for site in results_per_site if site not in SCRAPERS]
    if unknown:
        raise ValueError(f"unknown site(s) {', '.join(unknown)} in results; available: {', '.join(SCRAPERS)}")

    top = pick(args.top, settings.top)
    hours = pick(args.hours, settings.hours)
    max_pages = pick(args.max_pages, settings.max_pages)
    numbers = [("--results", results), ("--top", top), ("--hours", hours), ("--max-pages", max_pages)]
    numbers += [(f"results for {site}", count) for site, count in results_per_site.items()]
    for name, value in numbers:
        if value < 1:
            raise ValueError(f"{name} must be at least 1")

    return SearchOptions(
        resume_path=resume,
        sites=sites,
        locations=pick(args.locations, settings.locations),
        keywords=keywords,
        experience=experience,
        only_new=pick(args.only_new, settings.only_new),
        history_path=settings.history_path,
        max_age_hours=hours,
        max_pages=max_pages,
        top_n=top,
        results=results,
        results_per_site=results_per_site,
        use_llm=not args.no_llm,
        headless=not args.show_browser,
        output_dir=args.output_dir,
    )


def parse_results(values: list[str]) -> tuple[int | None, dict[str, int]]:
    """Split ['15'] / ['linkedin=20', 'naukri=12'] into (all-sites count, per-site counts)."""
    everywhere, per_site = None, {}
    for value in values:
        site, _, count = value.rpartition("=")
        try:
            number = int(count)
        except ValueError:
            raise ValueError(f"--results expects a number or SITE=NUMBER, got {value!r}") from None
        if site:
            per_site[site.strip().lower()] = number
        else:
            everywhere = number
    return everywhere, per_site


def print_summary(result) -> None:
    profile = result.profile
    if profile.summary:
        print(f"\nProfile: {profile.summary}")
    if profile.skills:
        print(f"Skills:  {', '.join(profile.skills[:10])}")

    for site, jobs in result.top_by_site.items():
        print(f"\n{site.title()} - top {len(jobs)}:")
        for rank, job in enumerate(jobs, start=1):
            score = "--" if job.score is None else f"{job.score:>3}"
            print(f"  {rank:>2}. [{score}] {job.title} - {job.company} ({job.location}, {job.posted_text or 'recent'})")
            if job.matched_skills:
                print(f"            Skills: {', '.join(job.matched_skills)}")
            print(f"            {job.url}")
    print(f"\nReport: {result.html_path}")
    print(f"All {len(result.jobs)} scored jobs: {result.xlsx_path}")
