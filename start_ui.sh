#!/usr/bin/env bash
# Start the job search web page (macOS / Linux): ./start_ui.sh
set -e
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate

# Build the web page the first time (needs Node.js 20+).
if [ ! -f frontend/out/index.html ]; then
  echo "Building the web page the first time, this takes a minute..."
  if ! command -v npm >/dev/null; then
    echo "Node.js is needed to build the page: install Node.js 20 or newer from https://nodejs.org" >&2
    exit 1
  fi
  (cd frontend && npm install && npm run build)
fi

exec python -m job_search "$@"
