"""Command line: `python -m job_search <serve|search|daily>`.

  serve   the local web app (default when no command is given)
  search  a one-off search from the command line
  daily   run the saved daily search once
  reset-password   set a new sign-in password (if you forgot it)
  copy-to-cloud    copy your data to the online (Vercel) database
"""

import sys

USAGE = (
    "usage: python -m job_search {serve,search,daily,reset-password,copy-to-cloud} [options]"
    "   (add --help after a command for its options)"
)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    command, rest = (argv[0], argv[1:]) if argv and not argv[0].startswith("-") else ("serve", argv)
    if command == "serve":
        from job_search.cli import serve

        return serve.main(rest)
    if command == "search":
        from job_search.cli import search

        return search.main(rest)
    if command == "daily":
        from job_search.cli import daily

        return daily.main(rest)
    if command == "reset-password":
        from job_search.cli import reset_password

        return reset_password.main(rest)
    if command == "copy-to-cloud":
        from job_search.cli import copy_to_cloud

        return copy_to_cloud.main(rest)
    print(USAGE, file=sys.stderr)
    return 2
