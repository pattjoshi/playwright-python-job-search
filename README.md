# Playwright Python Job Search

Give it your resume, and it finds jobs **posted in the last 24 hours** that match you,
ranked by an AI match score. Results open as an HTML page (top 10 per job site by default)
showing each job's link, matching skills and missing skills. Every scored job is also saved to Excel.

```
resume.pdf ─► OpenAI reads it ─► search phrases + location
                                        │
                                        ▼
                    Playwright searches job boards (past 24h filter)
                                        │
                                        ▼
               de-duplicate ─► open top jobs ─► OpenAI scores each 0-100
                                        │
                                        ▼
          output/jobs_YYYYMMDD_HHMM.html  (top N per site, opens automatically)
          output/jobs_YYYYMMDD_HHMM.xlsx  (+ .csv, every scored job)
```

| Board    | Status      | Login needed |
|----------|-------------|--------------|
| LinkedIn | ✅ working  | No (uses public job pages) |
| Naukri   | 🔜 planned  | – |
| Indeed   | 🔜 planned  | – |

## Setup (one time)

Needs Python 3.10+.

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and paste your OpenAI key into `OPENAI_API_KEY`. `.env` is git-ignored, so the key
never gets committed.

## Run it

```bash
python -m job_search --resume path/to/your_resume.pdf
```

Useful options:

| Option | What it does |
|--------|--------------|
| `--results 20` | Show the top 20 jobs per site in the HTML report (default 10) |
| `--location "Bengaluru"` | Override the location the AI found in your resume |
| `--keywords "SDET" "Python Developer"` | Override the search phrases |
| `--hours 12` | Only jobs from the last 12 hours (default 24) |
| `--top 20` | Jobs per site to open and score (faster, cheaper; default 40) |
| `--no-open` | Don't open the HTML report in your browser when finished |
| `--show-browser` | Watch Chrome do the work |
| `--no-llm` | No OpenAI at all; rank by keyword overlap (needs `--keywords`) |

When it finishes, the HTML report opens in your browser. Each job card shows the match score,
a link to the job, **matching skills** (green), **missing skills**, and a one-line reason,
ranked best first. The terminal shows the same list:

```
Linkedin - top 10:
   1. [ 92] SDET - Playwright - Globex (Pune, Maharashtra, India, 2 hours ago)
            Skills: Python, Playwright, pytest, REST API testing
            https://in.linkedin.com/jobs/view/...
  ...
Report: output/jobs_20261002_0915.html
All 40 scored jobs: output/jobs_20261002_0915.xlsx
```

Cost: one OpenAI call to read the resume plus one call per 10 jobs scored. With a small model
like the default `gpt-5.4-mini`, a full run costs a few cents. Change the model with
`OPENAI_MODEL` in `.env`.

## Project layout

```
job_search/
  cli.py          command-line options
  pipeline.py     the end-to-end flow (search, de-dupe, filter, score, report)
  resume.py       PDF / DOCX / TXT -> text
  llm.py          OpenAI: resume -> profile, and job scoring
  scrapers/
    base.py       interface every job board implements
    linkedin.py   LinkedIn public job search
  html_report.py  HTML page: top N jobs per site with skills and links
  report.py       Excel + CSV output
tests/            offline tests (saved HTML pages, mocked OpenAI)
```

### Adding a new job board

Create `job_search/scrapers/<board>.py` with a class that extends `BaseScraper` and implements
`search(query, location)` (and `fetch_description(job)` if search results lack the full
description), then register it in `job_search/scrapers/__init__.py`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests never touch the real sites. They use saved HTML in `tests/fixtures/` and a fake OpenAI client.

## Good to know

- **Be polite.** The tool waits 2-5 seconds between requests and reads only a few pages. If
  LinkedIn answers `429`, it stops and keeps what it already found; just try again later.
- **Sites change their HTML.** If a board suddenly returns 0 jobs, run with `--show-browser`,
  then update the CSS selectors at the top of that board's scraper file.
- **Terms of service.** Job boards restrict automated access. Keep this for personal,
  low-volume use.

## Roadmap

1. ~~Foundation + LinkedIn + OpenAI scoring + Excel report~~
2. Naukri (log in once, reuse the saved session)
3. Indeed
4. Remember already-seen jobs (SQLite) so each run shows only new ones
5. Daily schedule + email / Telegram alert
