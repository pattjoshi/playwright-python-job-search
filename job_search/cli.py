"""Command-line entry point: python -m job_search --resume my_resume.pdf"""

import argparse
import logging
import webbrowser
from pathlib import Path

from openai import OpenAIError

from job_search.config import load_settings
from job_search.pipeline import SearchOptions, run
from job_search.scrapers import SCRAPERS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job_search",
        description="Find recent jobs that match your resume.",
    )
    parser.add_argument("--resume", required=True, type=Path, help="Path to your resume (.pdf, .docx, .txt)")
    parser.add_argument(
        "--sites",
        nargs="+",
        choices=sorted(SCRAPERS),
        default=sorted(SCRAPERS),
        help="Job boards to search (default: all)",
    )
    parser.add_argument("--location", help="Override the location found in your resume, e.g. 'Bengaluru'")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=[],
        help="Override search phrases, e.g. --keywords 'Python Developer' 'SDET'",
    )
    parser.add_argument("--hours", type=int, default=24, help="Only jobs posted within this many hours (default 24)")
    parser.add_argument("--max-pages", type=int, default=3, help="Result pages per search (default 3)")
    parser.add_argument(
        "--results", type=int, default=10, help="Jobs per site to show in the HTML report, best first (default 10)"
    )
    parser.add_argument("--top", type=int, default=40, help="Jobs per site to open and score (default 40)")
    parser.add_argument("--no-llm", action="store_true", help="Skip OpenAI; rank by keyword overlap instead")
    parser.add_argument("--show-browser", action="store_true", help="Watch the browser while it works")
    parser.add_argument("--no-open", action="store_true", help="Don't open the HTML report when finished")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Where to save reports")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug logs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.no_llm and not args.keywords:
        parser.error("--no-llm needs --keywords, since there is no AI to read your resume")
    if args.results < 1:
        parser.error("--results must be at least 1")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep third-party HTTP chatter out of normal output.
    for noisy in ("httpx", "openai", "pdfminer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    options = SearchOptions(
        resume_path=args.resume,
        sites=args.sites,
        location=args.location,
        keywords=args.keywords,
        max_age_hours=args.hours,
        max_pages=args.max_pages,
        # Can't show more jobs than we score.
        top_n=max(args.top, args.results),
        results_per_site=args.results,
        use_llm=not args.no_llm,
        headless=not args.show_browser,
        output_dir=args.output_dir,
    )
    try:
        result = run(options, load_settings())
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
