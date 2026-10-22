"""Where the project's folders are, so the app works the same from any working directory."""

from pathlib import Path

# backend/src/job_search/config/paths.py -> config -> job_search -> src -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ENV = PROJECT_ROOT / ".env"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
# `npm run build` in frontend/ writes the static web page here; the backend serves it.
FRONTEND_BUILD_DIR = PROJECT_ROOT / "frontend" / "out"
