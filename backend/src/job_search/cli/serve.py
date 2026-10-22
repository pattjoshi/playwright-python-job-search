"""`python -m job_search serve`: start the local web app and open it in the browser."""

import argparse
import logging
import threading
import webbrowser

from job_search.cli.logs import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m job_search serve", description="Open the job search web UI.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="Don't open the browser automatically")
    args = parser.parse_args(argv)
    setup_logging()

    from job_search.api.app import create_app  # imported here so `--help` stays fast

    try:
        app = create_app()
    except ValueError as error:  # e.g. a bad value in .env
        logging.error("%s", error)
        return 1

    import uvicorn

    url = f"http://127.0.0.1:{args.port}"
    print(f"\n  Job search is running at {url}\n  Press Ctrl+C to stop.\n")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0
