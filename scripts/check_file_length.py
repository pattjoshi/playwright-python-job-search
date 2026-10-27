"""Fail when a source file has 250 lines or more (project rule: keep every file small and focused).

Usage: python scripts/check_file_length.py [--max 250]
Checks tracked and new files under backend/, frontend/ and scripts/ (code and styles, not docs or test fixtures).
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".css"}
SKIP_PARTS = {"node_modules", ".next", "out", "fixtures", "__pycache__"}
SKIP_NAMES = {"next-env.d.ts"}


def source_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "backend", "frontend", "scripts"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    files = [ROOT / name for name in listed]
    return [
        path for path in files
        if path.suffix in SUFFIXES and path.name not in SKIP_NAMES and not SKIP_PARTS & set(path.parts) and path.exists()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max", type=int, default=250, help="files must have fewer lines than this")
    limit = parser.parse_args().max

    too_long = []
    for path in source_files():
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines >= limit:
            too_long.append((lines, path.relative_to(ROOT)))
    for lines, path in sorted(too_long, reverse=True):
        print(f"{path}: {lines} lines (must be under {limit}); split it into smaller modules")
    if too_long:
        return 1
    print(f"All source files are under {limit} lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
