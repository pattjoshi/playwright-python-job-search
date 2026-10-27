"""Vercel entry point: the FastAPI app as one Python function, serving every /api/* request.

The page itself (frontend/out) is served by Vercel directly. Data lives in the DATABASE_URL Postgres database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from job_search.api.app import create_app  # noqa: E402 (needs the path above)

app = create_app()
