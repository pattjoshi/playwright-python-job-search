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
- `services/llm_service.py`: strict JSON-schema output with fallback, parallel scoring batches, `TokenUsage`.
- `api/app.py`: `create_app(settings, output_dir, upload_dir, runner, analyzer, system_scheduler,
  frontend_dir)`, the factory tests use with fakes. `api/routes/*`: one `build_router(ctx)` per resource.
  `ApiError` becomes `{"error": message}`. The built page is mounted last at `/`.
- Auth: `services/auth/` (`AuthService`, scrypt `passwords.py`, `LoginThrottle`), `repositories/user_repository.py`,
  `api/auth.py` (middleware: `/api/*` and `/reports/*` need a session cookie except `/api/auth/*`; cross-site
  writes refused; `current_user`/`require_owner` helpers), `api/routes/auth.py`. Tests sign in with
  `tests/auth_helpers.signed_in(client)`.
- Application tracker: `repositories/application_repository.py` (applications + their status-change events,
  per user; `stats()` for the dashboard), `services/applications.py` (`STATUSES`, validation in `clean()`,
  `ApplicationService.track_job()` used by `/api/applications/track` and by marking a job applied),
  `api/routes/applications.py`.
- Answer Bank: `repositories/answer_repository.py` (answers + `answer_wordings`, the other ways forms asked each
  question, also the cache of AI matches), `services/answers/` (`AnswerService.resolve()` answers a form question:
  saved wording → AI match → AI draft from the resume (`needs_review`) → else added as `needs_answer`; the AI never
  invents personal facts; `starters.py`, `ai.py` prompts, `matching.py`), `api/routes/answers.py`. `create_app(answer_ai=)`
  takes a factory so tests use `tests/answer_fakes.py` instead of OpenAI.
- Auto-apply: scrapers set `Job.apply_url` (the company page behind "Apply on company site";
  `services/scraping/apply_links.py`), cached in `job_details`. `repositories/auto_apply_repository.py` (queue + settings),
  `services/auto_apply/`: `service.py` (queue rules, limits, `run()`), `applier.py` (`apply_one`: open → click Apply →
  read form → fill → screenshot → submit → confirm), `form_fields.py` (in-page JS reads fields and tags them `data-ja`),
  `filler.py` (resume upload, AI cover letter, else `AnswerService.resolve`; only required unknowns are added to the
  bank), `platforms.py`, `manager.py` (background thread). Queued after each search via `SearchManager(after_search=)`
  and `cli/daily.auto_apply_matches`. `create_app(auto_apply_browser=)`; tests use saved forms in `tests/fixtures/forms`
  served locally (`tests/integration/form_site.py`); never open real career pages in tests.
  Board Easy Apply: `services/auto_apply/boards/` (`base.Board`: `ensure_login`, human pacing, security-check waits,
  `step_through` Next→Submit; `naukri.py` chat questions, `linkedin.py` pop-up, `indeed.py` new tab). Logins come
  from `Settings.board_logins` (`NAUKRI_EMAIL`/`_PASSWORD`…, `repr=False`); `browser.py` keeps a persistent profile in
  `data/browser-profile`. Per-board switches + `board_daily_limit` in settings; tests pass `board_base_url` and
  `pace=0` to use the saved board pages in `tests/fixtures/forms`. A run keeps ONE tab open (a visible Chrome quits
  with its last tab); `sessions.py` remembers boards you signed in to ("Sign in" = `AutoApplyManager.sign_in`, a
  visible browser waiting while you log in, so `.env` passwords are optional) and saves the page of jobs that didn't go
  through (served only as a download). `run(only_job=)` is "Try this job". Board pages wait for their Apply button
  (`Board.wait_until`) and report signed-out pages; LinkedIn opens `www.linkedin.com/jobs/view/<id>/`.
- Chrome extension (`extension/`, Manifest V3, plain JS, no build): applies to queued board jobs in the user's own
  signed-in Chrome. `api/routes/extension.py` (`/api/extension/*`, signed in with `Authorization: Bearer <key>` instead of
  a cookie, see `api/auth.py`), `services/auto_apply/extension_keys.py` (one key, only its hash stored) and
  `extension_bridge.py` (claim next job, answer, write, report). `tests/integration/test_chrome_extension.py` loads the
  extension in Chromium (`--headless=new`) against the real app and saved board pages.
- Notes: `notes` table (blocks as JSON, `parent_id` for pages inside pages, cascade delete), `repositories/note_repository.py`,
  `services/notes.py` (`clean_blocks`, `move` refuses loops), `api/routes/notes.py`.
- `cli/`: `serve`, `search`, `daily`, `reset-password` commands; `__main__.py` and `daily.py` are thin entry points.

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
  sheet; `statuses.ts` holds the status labels and colours), `answers/` (Answer Bank: tabs by status, rows
  grouped by category with an answer box shaped by `kind`, form dialog, Test a question card; `meta.ts`), `auto-apply/`
  (run card, queue tabs, job rows, settings with a confirm before leaving dry run), `notes/` (Notion-style:
  `NoteTree` sidebar, `NoteEditor` autosaves, `NoteBlock` = one auto-growing textarea per block with Markdown shortcuts,
  the "/" menu and dnd-kit sortable; pure helpers in `blocks.ts`), `settings/`, `coming-soon/`.
- `hooks/`: `useSearchForm`, `useSearchJob`, `useResume`, `useJobHistory`, `useDailySearch`,
  `useSessionRestore`, `useRuns`, `useApplications` (optimistic moves with rollback), `useApplicationStats`,
  `useAnswers`, `useSearchFilters` (hidden companies: one module-level store shared by `search-form/ExcludeCompaniesField`
  and the results), `useAutoApply` (polls while a run is going), `useNotes`.
- `lib/`: `api/` (typed client), `types.ts` (mirrors the API JSON), `format.ts`, `estimate.ts`, `funnel.ts`,
  `storage.ts`, `constants.ts`, `utils.ts` (`cn`).

Use theme tokens (`bg-card`, `text-muted-foreground`, `bg-success-soft`…), never raw colours. Give
one-column grids `grid-cols-1` so long text can't widen the page.

If an API response shape changes, update `lib/types.ts` and tests on both sides together.

## Adding a job board

Create `backend/src/job_search/services/scraping/<board>.py` extending `BaseScraper` (implement
`search()`, and `fetch_description()` if results lack the description), register it in
`services/scraping/__init__.py`, and add fixture-based tests (never call live sites in tests).
