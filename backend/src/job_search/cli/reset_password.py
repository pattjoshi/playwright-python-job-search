"""`python -m job_search reset-password`: set a new password without the old one.

Only someone at this computer can run it, which is the same trust as reading the data folder.
"""

import argparse
import getpass
import sys

from job_search.config import load_settings
from job_search.repositories import UserRepository
from job_search.services.auth import AuthError, AuthService


def main(argv: list[str] | None = None, read_password=getpass.getpass) -> int:
    parser = argparse.ArgumentParser(prog="python -m job_search reset-password", description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True, help="The email you sign in with")
    args = parser.parse_args(argv)

    auth = AuthService(UserRepository(load_settings().history_path))
    new = read_password("New password: ")
    if new != read_password("Type it again: "):
        print("The two passwords don't match. Nothing changed.", file=sys.stderr)
        return 1
    try:
        user = auth.reset_password(args.email, new)
    except AuthError as error:
        print(error.message, file=sys.stderr)
        return 1
    print(f"Password changed for {user.email}. Every browser was signed out; sign in again.")
    return 0
