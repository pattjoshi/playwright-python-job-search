# CLAUDE.md

Guidance for Claude Code (claude.ai/code) and other AI coding tools working in this repository.
Human contributors: see [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

A local tool that searches LinkedIn, Naukri and Indeed with Playwright, then uses OpenAI to read the
user's resume and score each job against it. Two parts:

- `backend/`: Python package `job_search` (FastAPI API, Playwright scrapers, OpenAI, SQLite).
- `frontend/`: Next.js + TypeScript page, exported as static files (`frontend/out`) that the
  backend serves at `/`, so users start everything with one command.

Nothing leaves the user's machine except resume text and job descriptions sent to OpenAI.

## Commands

```bash
pip install -e "./backend[dev]"      # backend + pytest/ruff (root requirements.txt = runtime only)
playwright install chromium
python -m job_search                 # web app on :8000 (same as `serve`); --no-open, --port N
python -m job_search search --resume cv.pdf --location Pune Remote --results linkedin=20
python -m job_search daily           # run the saved daily search once (Task Scheduler / cron call
                                     # `python -m job_search.daily`, kept for older installs)

cd backend && ruff check . && pytest            # tests/unit fast, tests/integration needs Chromium
cd frontend && npm install
npm run dev                          # :3000, proxies /api and /reports to the backend on :8000
npm run lint && npm run typecheck && npm test && npm run build
python scripts/check_file_length.py  # every source file must stay under 250 lines (CI enforces it)
```

## Branches

`main` (stable) ← `develop` (integration) ← `feature/*`, `fix/*`, `docs/*`, `chore/*`.
Branch from `develop`, open pull requests into `develop`. Never push to `main` or `develop` directly.

## Backend architecture (`backend/src/job_search/`)

Layered: **api / cli → services → repositories → models**, with `config/`, `schemas/`, `database/`
supporting. Lower layers never import upper ones.

- `models/`: plain dataclasses (`Job`, `Profile`, `SearchOptions`, `RunStats`, `SearchResult`, `Schedule`).
- `database/`: SQLAlchemy `Base`, `tables.py` (models for the app DB `data/history.sqlite3`), Alembic
  `migrations/` applied automatically by `get_engine(path)`; `test_database.py` fails if models drift
  from migrations. The disposable cache DB still uses the raw `Database` helper.
- `config/`: `Settings`/`load_settings()` from `.env` (command line wins), `paths.py` (project root,
  `data/`, `output/`, `uploads/`, `frontend/out`, all anchored to the repo root), city list.
- `repositories/`: `JobHistoryRepository` (SQLAlchemy) (applied/hidden/seen + run history, never
  auto-deleted) and `CacheRepository` (resume readings, descriptions, scores; safe to delete),
  plus JSON session/schedule files.
- `services/search/`: the search. `runner.run()` is the entry point (timing, run history), and
  `pipeline.run_pipeline()` runs the steps (resume → profile → sites → filters → details → score →
  report). `sites.py` handles per-site browser work (`collect_site`, `fetch_details`,
  `on_each_site`), `filters.py` builds the funnel, and `profile.py` covers resume reading and default
  locations. Progress goes out through an `on_event(name, data)` callback (`stage`, `profile`,
  `site`, `progress`, `funnel`).
- `services/scraping/`: `BaseScraper` (retries on 429/503, `unreachable` after repeated failures,
  `pause()` respects Stop), the three boards, and `SiteSession` (**one Playwright browser per
  site on its own thread**: the sync API is thread-bound). `SCRAPERS` registers boards.
- `services/search_manager.py`: one search at a time on a background thread for the web page
  (poll + Stop), and it saves the last search to the session so reloads restore it.
- `services/llm_service.py`: strict JSON-schema output with fallback, parallel scoring batches, `TokenUsage`.
- `api/app.py`: `create_app(settings, output_dir, upload_dir, runner, analyzer, system_scheduler,
  frontend_dir)`, the factory tests use with fakes. `api/routes/*`: one `build_router(ctx)` per resource.
  `ApiError` becomes `{"error": message}`. The built page is mounted last at `/`.
- `cli/`: `serve`, `search`, `daily` commands; `__main__.py` and `daily.py` are thin entry points.

Tests patch `job_search.services.search.pipeline.SCRAPERS` / `.JobMatcherLLM` to fake boards and AI.
Calling `run()` always starts real Chromium (via `SiteSession`), so such tests live in `integration/`.

## Frontend architecture (`frontend/src/`)

Tailwind CSS v4 + shadcn/ui (new-york). Theme tokens in `styles/theme.css` (light + `.dark`), dark mode via
next-themes, toasts via sonner. Static export: pages become `name.html`, served by the backend at `/name`.

- `app/layout.tsx` (theme provider, toaster); `app/page.tsx` redirects to `/dashboard`;
  `app/(app)/layout.tsx` wraps every page in `ConfigProvider` → `SearchSessionProvider` → `AppShell`;
  `app/(app)/<page>/page.tsx` exports metadata and renders a feature component.
- `providers/`: `ConfigProvider` (`useConfig`, loads `/api/config` once), `SearchSessionProvider`
  (`useSearchSession`: form, resume, running search, history, daily search and actions; lives above the
  pages so navigation keeps state and a running search), `ThemeProvider`.
- `components/ui/`: shadcn components (copied from the registry; `Button` defaults to `type="button"`)
  plus small custom parts (`stepper`, `tag-input`, `form-field`, `step-title`, `chip`).
- `components/layout/`: `AppShell`, `AppSidebar`, `Topbar`, `nav.ts` (sidebar items; `soon` = later phase),
  `PageHeader`. Feature folders: `dashboard/`, `search/`, `resume/`, `search-form/`, `daily/`, `progress/`,
  `results/`, `my-jobs/`, `settings/`, `coming-soon/`.
- `hooks/`: `useSearchForm`, `useSearchJob`, `useResume`, `useJobHistory`, `useDailySearch`,
  `useSessionRestore`, `useRuns`.
- `lib/`: `api/` (typed client), `types.ts` (mirrors the API JSON), `format.ts`, `estimate.ts`, `funnel.ts`,
  `storage.ts`, `constants.ts`, `utils.ts` (`cn`).

Use theme tokens (`bg-card`, `text-muted-foreground`, `bg-success-soft`…), never raw colours. Give
one-column grids `grid-cols-1` so long text can't widen the page.

If an API response shape changes, update `lib/types.ts` and tests on both sides together.

## Adding a job board

Create `backend/src/job_search/services/scraping/<board>.py` extending `BaseScraper` (implement
`search()`, and `fetch_description()` if results lack the description), register it in
`services/scraping/__init__.py`, and add fixture-based tests (never call live sites in tests).
