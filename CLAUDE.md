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
  `profile.search_queries()` dedupes and caps keywords at `MAX_QUERIES` (the resume prompt asks for 6-10 short job
  titles; bump `PROFILE_VERSION` when that prompt changes). Boards set `cities_per_search` (Naukri 3) and
  `matching_service.search_locations` groups cities to match. Speed: `collect_site(cache=)` reuses a site's results for a
  `search_key` (site, keyword, city, hours, experience, pages) for `SEARCH_REUSE_HOURS` (cache table `searches`; refused
  searches aren't saved); `BaseScraper.nothing_new()` ends a search when a page only repeats jobs found earlier this run.
  `apply_filters(queries=, terms=)` adds the "title fits" step (`matching_service.title_fits`), `Job.dedupe_key` normalises
  Sr/Pvt Ltd/(Remote)/city, and results sort by `rank_key` (score, then newest).
- `services/scraping/`: `BaseScraper` (retries on 429/503, `unreachable` after repeated failures,
  `pause()` respects Stop), the three boards, and `SiteSession` (**one Playwright browser per
  site on its own thread**: the sync API is thread-bound). `SCRAPERS` registers boards. `browser.launch()` prefers the
  installed Google Chrome (`channel="chrome"`) with `--disable-blink-features=AutomationControlled` and a normal user
  agent (no "HeadlessChrome"): Naukri answers "Access Denied" otherwise. A scraper sets `blocked` on that page, which
  stops the site for the run (status `blocked`); Naukri opens its home page once before searching.
- Hidden companies: `repositories/search_filters_repository.py` (`data/search-filters.json`), `services/search_filters.py`
  (`company_key` drops Pvt/Ltd/Inc… so names match; same rule in `frontend/src/lib/results-filter.ts`), `api/routes/search_filters.py`.
  `apply_filters(exclude_companies=)` adds the "not from hidden companies" funnel step. `job_to_dict` sends `hours_ago`
  and the description (cut to `MAX_DESCRIPTION`) for the results filters and details panel.
- `services/search_manager.py`: one search at a time on a background thread for the web page
  (poll + Stop), and it saves the last search to the session so reloads restore it.
- OpenAI key: `services/openai_key.py` (`OpenAIKeyService`: saved key wins over `.env`, checked with `models.list()` before saving,
  `hint()` only ever sent back; `with_saved_key(settings)` attaches it, so always call `settings.api_key()`, never
  `settings.openai_api_key`), `repositories/secret_store.py` (Fernet, `data/secrets.json` 0600, key from `APP_SECRET` or
  `data/secret.key`), `api/routes/openai_key.py` (owner-only PUT/DELETE). Tests pass `create_app(key_checker=)`.
- `services/llm_service.py`: strict JSON-schema output with fallback, parallel scoring batches, `TokenUsage`. Scoring sends
  `services/job_text.clean_description()` (drops company intro / benefits / EEO sections and lines, cut to `MAX_DESCRIPTION_CHARS`).
- `api/app.py`: `create_app(settings, output_dir, upload_dir, runner, analyzer, system_scheduler,
  frontend_dir)`, the factory tests use with fakes. `api/routes/*`: one `build_router(ctx)` per resource.
  `ApiError` becomes `{"error": message}`. The built page is mounted last at `/` (`api/frontend.PageFiles`: `_next/static/*`
  is cached for good, `IMMUTABLE`); responses over 1 KB are gzipped (`GZipMiddleware`).
- Security (`api/security.py`, added last so it runs first): Host must be 127.0.0.1/localhost/::1 (+ `ALLOWED_HOSTS`;
  stops DNS rebinding), bodies over `MAX_BODY_BYTES` refused, `nosniff`/`DENY`/`frame-ancestors`/`Referrer-Policy` headers.
  Scraped data is untrusted: `excel_csv.as_text()` (no formulas, only http(s) hyperlinks).
  Tests use `TestClient(app, base_url="http://127.0.0.1")`.
- Auth: `services/auth/` (`AuthService`, scrypt `passwords.py`, `LoginThrottle`), `repositories/user_repository.py`,
  `api/auth.py` (middleware: `/api/*` and `/reports/*` need a session cookie except `/api/auth/*`; writes need an Origin
  equal to the Host or `DEV_ORIGINS` (`npm run dev`); `current_user`/`require_owner` helpers), `api/routes/auth.py`. Tests sign in with
  `tests/auth_helpers.signed_in(client)`.
- Application tracker: `repositories/application_repository.py` (applications + their status-change events,
  per user; `stats()` for the dashboard), `services/applications.py` (`STATUSES`, validation in `clean()`,
  `ApplicationService.track_job()` used by `/api/applications/track` and by marking a job applied),
  `api/routes/applications.py`.
- Notes: `notes` table (blocks as JSON, `parent_id` for pages inside pages, cascade delete), `repositories/note_repository.py`,
  `services/notes.py` (`clean_blocks`, `move` refuses loops), `api/routes/notes.py`.
- Online (Vercel, see DEPLOY.md): `api/index.py` (repo root) is the function, `vercel.json` builds `frontend/out` and rewrites
  `/api/*` to it, `api/requirements.txt` its packages (Playwright's driver excluded). `database/engine.get_engine()` uses
  `DATABASE_URL` (Postgres, `NullPool`) when set, else the SQLite file; repositories must stay dialect-neutral
  (`history_repository._upsert()`). `config.paths.HOSTED` (VERCEL/HOSTED env): files under /tmp, `Settings.hosted`,
  `setup_code` (first account needs it), Vercel URLs added to `allowed_hosts`, Secure cookie, `client_address()` from
  X-Forwarded-For, `security.LOCAL_ONLY` routes refused (409); the page hides Search (`nav.LOCAL_ONLY_PATHS`, `LocalOnly`).
  `cli/copy_to_cloud.py` copies users/applications/notes/jobs/runs once. Tests: `TEST_DATABASE_URL=postgresql://… pytest`
  runs everything on Postgres (fresh schema per test; CI job `backend-postgres`).
- `cli/`: `serve`, `search`, `daily`, `reset-password`, `copy-to-cloud` commands; `__main__.py` and `daily.py` are thin entry points.

Tests patch `job_search.services.search.pipeline.SCRAPERS` / `.JobMatcherLLM` to fake boards and AI.
Calling `run()` always starts real Chromium (via `SiteSession`), so such tests live in `integration/`.

## Frontend architecture (`frontend/src/`)

Tailwind CSS v4 + shadcn/ui (new-york). Theme tokens in `styles/theme.css` (light + `.dark`), dark mode via
next-themes, toasts via sonner. Static export: pages become `name.html`, served by the backend at `/name`.

- `app/layout.tsx` (theme provider, toaster); `app/page.tsx` is the public home page (`components/home/`);
  `app/login/page.tsx` signs in or creates the first account (`components/auth/`);
  `app/(app)/layout.tsx` wraps every page in `AuthProvider` (guard) → `ConfigProvider` → `SearchSessionProvider` → `AppShell`;
  any 401 from the API redirects to `/login?next=…`;
  `app/(app)/<page>/page.tsx` exports metadata and renders a feature component.
- `providers/`: `ConfigProvider` (`useConfig`, loads `/api/config` once), `SearchSessionProvider`
  (`useSearchSession`: form, resume, running search, history, daily search and actions; lives above the
  pages so navigation keeps state and a running search), `ThemeProvider`.
- `components/ui/`: shadcn components (copied from the registry; `Button` defaults to `type="button"`)
  plus small custom parts (`stepper`, `tag-input`, `form-field`, `step-title`, `chip`).
- `components/layout/`: `AppShell`, `AppSidebar`, `Topbar`, `nav.ts` (sidebar items; `soon` = later phase),
  `PageHeader`. Feature folders: `dashboard/`, `search/`, `resume/`, `search-form/`, `daily/`, `progress/`,
  `results/` (`ResultsFilters` toolbar, `JobDetailsSheet`; filtering in `lib/results-filter.ts`), `my-jobs/`, `applications/` (board with dnd-kit drag and drop, table, form dialog, details
  sheet; `statuses.ts` holds the status labels and colours), `notes/` (Notion-style:
  `NoteTree` sidebar, `NoteEditor` autosaves, `NoteBlock` = one auto-growing textarea per block with Markdown shortcuts,
  the "/" menu and dnd-kit sortable; pure helpers in `blocks.ts`), `settings/`, `coming-soon/`.
- `hooks/`: `useSearchForm`, `useSearchJob`, `useResume`, `useJobHistory`, `useDailySearch`,
  `useSessionRestore`, `useRuns`, `useApplications` (optimistic moves with rollback), `useApplicationStats`,
  `useSearchFilters` (hidden companies: one module-level store shared by `search-form/ExcludeCompaniesField`
  and the results), `useNotes`.
- `lib/`: `api/` (typed client), `types.ts` (mirrors the API JSON), `format.ts`, `estimate.ts`, `funnel.ts`,
  `storage.ts`, `constants.ts`, `utils.ts` (`cn`), `poll.ts` (`waitForNextPoll`: `POLL_MS`, `HIDDEN_POLL_MS` in a background tab,
  at once on return; used by `useSearchJob`).

Use theme tokens (`bg-card`, `text-muted-foreground`, `bg-success-soft`…), never raw colours. Give
one-column grids `grid-cols-1` so long text can't widen the page.

If an API response shape changes, update `lib/types.ts` and tests on both sides together.

## Adding a job board

Create `backend/src/job_search/services/scraping/<board>.py` extending `BaseScraper` (implement
`search()`, and `fetch_description()` if results lack the description), register it in
`services/scraping/__init__.py`, and add fixture-based tests (never call live sites in tests).
