"""`python -m job_search.daily`: the command saved in Task Scheduler / cron for the daily search.

Kept at this path so daily searches set up with older versions keep working.
"""

from job_search.cli.daily import main

if __name__ == "__main__":
    raise SystemExit(main())
