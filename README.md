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
| Naukri   | ✅ new      | No |
| Indeed   | ✅ new      | No (may show a "verify you are human" check; keep the browser visible to solve it) |

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

## Web UI (easiest)

```bash
python -m job_search.web
```

On Windows you can also just double-click **`start_ui.bat`**.

Your browser opens <http://127.0.0.1:8000>:

1. **Drop in your resume.** It's read right away: keywords, your city and a matching
   experience range are filled in for you.
2. **Adjust anything:** keywords (add/remove), **locations** (pick several Indian tech cities
   and/or **Remote**, or type any city), **experience** (e.g. 1 to 2 years, or Any), how recent
   the posts should be, and **how many jobs to show from each site** (e.g. LinkedIn 20,
   Naukri 12, Indeed 10).
3. Press **Start search**. Watch each step and site live; press **Stop** any time.
4. Results come in tabs per site, best match first, each with a link, match score, matching
   and missing skills. Click **Mark applied** or **Hide** and that job never shows up again.
   Turn on **Only new jobs** to skip anything you were shown before.

Your choices are remembered for next time. The app only runs on your own computer; press
Ctrl+C in the terminal to stop it.

### Daily search

In the **Daily search** card, pick a time (e.g. 9:00 AM) and the days, then press
**Save daily search**. It saves the search settings shown on the page and registers a task
with **Windows Task Scheduler** (cron on macOS/Linux), so it runs even when the web page is
closed. When it finishes, the HTML report opens in your browser. If the laptop was off or
asleep at that time (Windows), it runs as soon as it's back on. The card shows the next run,
the last run with a link to its report, and a **Turn off** button.

You can also run the saved search by hand: `python -m job_search.daily` (log: `data/scheduled.log`).

## Command line

```bash
python -m job_search --resume path/to/your_resume.pdf
```

### Save your defaults in `.env`

Instead of typing options every day, set them once in `.env`:

```ini
RESUME=Omprakash_Resume.pdf
LOCATION=Bengaluru
KEYWORDS=Python Automation Engineer, SDET
RESULTS=20
```

Then a daily run is just:

```bash
python -m job_search
```

Every `.env` setting matches a command-line option (`RESULTS` = `--results`, `LOCATION` =
`--location`, and so on). An option typed on the command line wins for that run, e.g.
`python -m job_search --results 5`. See `.env.example` for the full list with explanations.

Useful options:

| Option | What it does |
|--------|--------------|
| `--results 20` | Show the top 20 jobs per site in the HTML report (default 10) |
| `--results linkedin=20 naukri=12` | A different number for each site |
| `--location Pune Remote` | Where to search (several allowed, "Remote" included) |
| `--experience 1-2` | Years of experience you want |
| `--only-new` | Skip jobs shown in earlier searches |
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
    naukri.py     Naukri search (reads the JSON the page loads)
    indeed.py     Indeed search (India site)
  html_report.py  HTML page: top N jobs per site with skills and links
  report.py       Excel + CSV output
  web.py          local web UI (Flask) + static/index.html
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

## Speed, cost and cleanup

- **Repeat runs are cheap.** Job descriptions, AI scores and the AI's reading of your resume are
  saved in `data/cache.sqlite3`. A job opened or scored before isn't opened or scored again (scores
  are redone automatically if your resume, experience range or model changes).
- **Faster pages.** Images, fonts and media aren't downloaded (styles too when the browser is hidden).
- **Fewer requests.** Naukri searches several cities in one go.
- **Sites in parallel.** LinkedIn, Naukri and Indeed are searched at the same time, each in its own
  browser (`PARALLEL_SITES=false` to go one by one). Each single site is still visited politely, one page at a time.
- **Parallel scoring.** Up to 4 AI scoring batches run at once.
- **Cost per run.** The results show run time, AI tokens and how many scores were reused. Add your
  model's prices to `.env` (`OPENAI_PRICE_INPUT`, `OPENAI_PRICE_OUTPUT`, optional
  `OPENAI_PRICE_CACHED_INPUT`, in USD per 1M tokens) to also see an estimated cost.
- **Search history.** *My jobs → Search history* lists every run (manual and daily): status, time,
  jobs found per site, the filter funnel, tokens/cost, errors and a link to its report.
- **Reliable.** Strict JSON schemas for AI replies; automatic retries when OpenAI or a job site says
  "too many requests"; a site that keeps failing is skipped for the rest of the run instead of
  slowing everything down.
- **Cleanup.** Uploaded resumes, reports and cached data older than `KEEP_DAYS` (default 30; `0` = keep
  forever) are deleted when the web app starts and after each daily run. Your job history, the
  resume used by the daily search and the last daily report are never deleted.

## Good to know

- **Be polite.** The tool waits 2-5 seconds between requests and reads only a few pages. If
  LinkedIn answers `429`, it stops and keeps what it already found; just try again later.
- **Sites change their HTML.** If a board suddenly returns 0 jobs, run with `--show-browser`,
  then update the CSS selectors at the top of that board's scraper file.
- **Terms of service.** Job boards restrict automated access. Keep this for personal,
  low-volume use.

## Roadmap

1. ~~Foundation + LinkedIn + OpenAI scoring + Excel report~~
2. ~~Settings in .env~~
3. ~~Naukri and Indeed, per-site result counts, web UI~~
4. ~~Remember seen jobs, only-new mode, applied/hide, experience filter, multi-location, stop~~
5. ~~Daily search at a chosen time (Task Scheduler / cron)~~
