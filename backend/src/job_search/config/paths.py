"""Where the project's folders are, so the app works the same from any working directory."""

import os
from pathlib import Path

# backend/src/job_search/config/paths.py -> config -> job_search -> src -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ENV = PROJECT_ROOT / ".env"
# Online (Vercel sets VERCEL=1) the project folder is read-only and wiped: the few files the app writes go to /tmp,
# and everything that must last is in the DATABASE_URL database.
HOSTED = bool(os.getenv("VERCEL") or os.getenv("HOSTED"))
FILES_ROOT = Path(os.getenv("JOB_SEARCH_HOME") or ("/tmp/job-search" if HOSTED else PROJECT_ROOT))
DATA_DIR = FILES_ROOT / "data"
OUTPUT_DIR = FILES_ROOT / "output"
UPLOAD_DIR = FILES_ROOT / "uploads"
# `npm run build` in frontend/ writes the static web page here; the backend serves it.
FRONTEND_BUILD_DIR = PROJECT_ROOT / "frontend" / "out"
