"""Self-contained HTML page of the top jobs per site, ranked best first."""

from datetime import datetime
from html import escape
from pathlib import Path

from job_search.models import Job, Profile

SITE_NAMES = {"linkedin": "LinkedIn", "naukri": "Naukri", "indeed": "Indeed"}

STYLE = """
:root {
  --bg: #f6f7f9; --card: #ffffff; --text: #1d2330; --muted: #5d6676; --border: #e2e5ea;
  --accent: #0a66c2; --good-bg: #e3f4e8; --good: #17663a; --ok-bg: #fdf1dc; --ok: #8a5300;
  --low-bg: #eceef2; --low: #4b5363; --chip-miss: #c9ced6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12151b; --card: #1b2029; --text: #e7eaf0; --muted: #9aa3b2; --border: #2c3340;
    --accent: #5aa9ff; --good-bg: #173b26; --good: #7fdc9f; --ok-bg: #3d2f12; --ok: #f2c46b;
    --low-bg: #262c37; --low: #b3bac6; --chip-miss: #3d4554;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 19px; margin: 36px 0 12px; }
.meta { color: var(--muted); margin: 0 0 20px; }
.panel { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }
.panel p { margin: 0 0 10px; }
ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.job { display: grid; grid-template-columns: 56px 1fr; gap: 14px; background: var(--card);
  border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }
.rank { color: var(--muted); font-size: 12px; text-align: center; }
.score { display: grid; place-items: center; width: 52px; height: 52px; border-radius: 50%;
  font-weight: 700; font-size: 17px; margin-bottom: 4px; }
.score.good { background: var(--good-bg); color: var(--good); }
.score.ok { background: var(--ok-bg); color: var(--ok); }
.score.low { background: var(--low-bg); color: var(--low); }
.title { font-size: 17px; font-weight: 600; color: var(--accent); text-decoration: none; }
.title:hover { text-decoration: underline; }
.sub { color: var(--muted); margin: 2px 0 8px; }
.label { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase;
  letter-spacing: .04em; margin-right: 6px; }
.chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 6px 0; }
.chip { font-size: 13px; padding: 2px 10px; border-radius: 999px; }
.chip.have { background: var(--good-bg); color: var(--good); }
.chip.miss { border: 1px solid var(--chip-miss); color: var(--muted); }
.chip.skill { background: var(--low-bg); color: var(--low); }
.reason { margin: 8px 0 10px; }
.open { display: inline-block; font-weight: 600; color: var(--accent); text-decoration: none; }
.open:hover { text-decoration: underline; }
.empty { color: var(--muted); }
@media (max-width: 520px) { .job { grid-template-columns: 1fr; } .rank { display: flex; gap: 10px; align-items: center; } }
"""


def write_html_report(
    profile: Profile,
    top_by_site: dict[str, list[Job]],
    path: Path,
    max_age_hours: int = 24,
    generated_at: datetime | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(profile, top_by_site, max_age_hours, generated_at or datetime.now()), encoding="utf-8")
    return path


def render_html(profile: Profile, top_by_site: dict[str, list[Job]], max_age_hours: int, generated_at: datetime) -> str:
    counts = " · ".join(f"{_site_name(site)}: {len(jobs)}" for site, jobs in top_by_site.items())
    sections = "".join(_site_section(site, jobs) for site, jobs in top_by_site.items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Matches</title>
<style>{STYLE}</style>
</head>
<body>
<main>
  <h1>Your job matches</h1>
  <p class="meta">Posted in the last {max_age_hours} hours · generated {generated_at:%d %b %Y, %H:%M} · {escape(counts)}</p>
  {_profile_panel(profile)}
  {sections}
</main>
</body>
</html>
"""


def _profile_panel(profile: Profile) -> str:
    if not (profile.summary or profile.skills):
        return ""
    summary = f"<p>{escape(profile.summary)}</p>" if profile.summary else ""
    skills = "".join(f'<span class="chip skill">{escape(skill)}</span>' for skill in profile.skills)
    skills_row = f'<div class="chips"><span class="label">Your skills</span>{skills}</div>' if skills else ""
    return f'<section class="panel">{summary}{skills_row}</section>'


def _site_section(site: str, jobs: list[Job]) -> str:
    heading = f"<h2>{escape(_site_name(site))} · top {len(jobs)}</h2>"
    if not jobs:
        return heading + '<p class="empty">No matching jobs found on this site in this window.</p>'
    items = "".join(_job_card(rank, job) for rank, job in enumerate(jobs, start=1))
    return f"{heading}<ol>{items}</ol>"


def _job_card(rank: int, job: Job) -> str:
    url = _safe_url(job.url)
    score = "–" if job.score is None else str(job.score)
    details = " · ".join(escape(part) for part in (job.company, job.location, job.posted_text) if part)
    matched = _chips("Matching", job.matched_skills, "have")
    missing = _chips("Missing", job.missing_skills, "miss")
    reason = f'<p class="reason">{escape(job.match_reason)}</p>' if job.match_reason else ""
    return f"""
<li class="job">
  <div class="rank"><div class="score {_score_band(job.score)}">{score}</div>#{rank}</div>
  <div>
    <a class="title" href="{url}" target="_blank" rel="noopener">{escape(job.title)}</a>
    <div class="sub">{details}</div>
    {matched}{missing}{reason}
    <a class="open" href="{url}" target="_blank" rel="noopener">View job &rarr;</a>
  </div>
</li>"""


def _chips(label: str, skills: list[str], kind: str) -> str:
    if not skills:
        return ""
    chips = "".join(f'<span class="chip {kind}">{escape(skill)}</span>' for skill in skills)
    return f'<div class="chips"><span class="label">{label}</span>{chips}</div>'


def _score_band(score: int | None) -> str:
    if score is None:
        return "low"
    if score >= 75:
        return "good"
    return "ok" if score >= 50 else "low"


def _safe_url(url: str) -> str:
    # Only real web links; anything else (e.g. "javascript:") becomes a dead link.
    return escape(url, quote=True) if url.startswith(("https://", "http://")) else "#"


def _site_name(site: str) -> str:
    return SITE_NAMES.get(site, site.title())
