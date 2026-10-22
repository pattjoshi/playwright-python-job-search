# Contributing

Thanks for helping! This guide explains how the branches work, how to set up the project for
development, and the rules every change follows.

## Branches

| Branch | What it is | Who changes it |
|---|---|---|
| `main` | The stable version people install. Always works. | Only by merging `develop` (a release) |
| `develop` | Where finished work comes together and is tested before a release | Only by merging pull requests |
| `feature/<short-name>` | One new feature, e.g. `feature/salary-filter` | You |
| `fix/<short-name>` | One bug fix, e.g. `fix/naukri-empty-results` | You |
| `docs/<short-name>`, `chore/<short-name>` | Docs only / tooling, dependencies, clean-up | You |

The flow:

```
feature/...  ──PR──▶  develop  ──PR (release)──▶  main
```

1. Start from the latest `develop`:

   ```bash
   git checkout develop
   git pull
   git checkout -b feature/salary-filter
   ```

2. Make small, focused commits (see [Commit messages](#commit-messages)).
3. Push the branch and open a **pull request into `develop`**. Fill in the template.
4. CI must be green, and the change gets a review before it is merged.
5. When `develop` is ready for a release, a pull request from `develop` into `main` is opened and merged.

Never push directly to `main` or `develop`, and keep one topic per branch: a bug fix found while working
on a feature goes in its own `fix/...` branch.

## Development setup

You need Python 3.10+, Node.js 20+ and Git.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e "./backend[dev]"        # backend + test and lint tools
playwright install chromium
cd frontend && npm install && cd ..
cp .env.example .env                   # then add your OPENAI_API_KEY
```

Run it with live reload in two terminals:

```bash
python -m job_search --no-open         # backend API on http://127.0.0.1:8000
cd frontend && npm run dev             # the page on http://localhost:3000
```

## Project layout

- `backend/src/job_search/`: the Python package.
  - `api/` has the FastAPI app and one router per resource.
  - `services/` has the business logic: search, scraping, AI, reports, schedule.
  - `repositories/` handles storage.
  - `models/` holds the dataclasses.
  - `cli/` has the commands.
- `backend/tests/`: `unit/` for fast tests without a browser, `integration/` for tests with a headless browser and fakes.
- `frontend/src/`: the Next.js page.
  - `components/` has `ui/` primitives plus one folder per feature.
  - `hooks/` holds state and API calls.
  - `lib/` holds the typed API client and helpers.

The README's [For developers](README.md#8-for-developers) section has the full tree.

## Rules for every change

- **Every source file stays under 250 lines.** Split big files into smaller modules with one clear job.
  CI checks this (`python scripts/check_file_length.py`).
- **Tests come with the change.** New behavior gets a test; a bug fix gets a test that failed before the fix.
  Tests never call the real job sites or OpenAI (use the fakes and saved pages in `backend/tests/fixtures`).
- **Match the code around you.** Python: type hints and a docstring on public functions; ruff must pass.
  TypeScript: strict mode, no `any`, one component per file, styles in a CSS Module next to the component.
- **The backend API is the contract.** If you change a response shape, update `frontend/src/lib/types.ts`
  and the tests on both sides in the same pull request.
- **No secrets or personal data** in commits: no `.env`, API keys, resumes, or files from `data/`, `uploads/` or `output/`.
- **Docs follow the code.** If you change how to install or use the app, update README.md / QUICKSTART.md.

## Before you open a pull request

Run the same checks as CI:

```bash
cd backend && ruff check . && pytest && cd ..
cd frontend && npm run lint && npm run typecheck && npm test && npm run build && cd ..
python scripts/check_file_length.py
```

## Commit messages

Write the subject in the imperative, under ~72 characters, describing what changes for the user or the code:

```
Add a minimum match score filter
Fix Naukri results missing when only Remote is picked
Split the scoring step out of the search pipeline
```

Add a body when the *why* isn't obvious from the subject.
