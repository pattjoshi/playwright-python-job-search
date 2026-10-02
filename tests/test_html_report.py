from datetime import datetime

from job_search.html_report import render_html, write_html_report
from job_search.models import Job, Profile


def make_job(rank, **kwargs):
    defaults = dict(
        source="linkedin",
        job_id=str(rank),
        title=f"Job {rank}",
        company="Acme",
        location="Pune",
        url=f"https://www.linkedin.com/jobs/view/{rank}",
    )
    return Job(**{**defaults, **kwargs})


def test_html_lists_jobs_in_order_with_skills_and_links():
    jobs = [
        make_job(1, score=91, matched_skills=["Python", "Playwright"], missing_skills=["Kubernetes"], match_reason="Strong fit"),
        make_job(2, score=55),
    ]
    html = render_html(Profile(summary="QA engineer", skills=["Python"]), {"linkedin": jobs}, 24, datetime(2026, 10, 2, 9, 15))

    assert "LinkedIn · top 2" in html
    assert html.index("Job 1") < html.index("Job 2")
    assert 'href="https://www.linkedin.com/jobs/view/1"' in html
    assert '<span class="chip have">Playwright</span>' in html
    assert '<span class="chip miss">Kubernetes</span>' in html
    assert "Strong fit" in html
    assert "last 24 hours" in html and "02 Oct 2026, 09:15" in html


def test_html_escapes_text_and_blocks_unsafe_links():
    job = make_job(1, title="<script>alert(1)</script>", url="javascript:alert(1)")
    html = render_html(Profile(), {"linkedin": [job]}, 24, datetime.now())

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="#"' in html


def test_empty_site_shows_message(tmp_path):
    path = write_html_report(Profile(), {"linkedin": []}, tmp_path / "out" / "r.html")
    assert "No matching jobs" in path.read_text(encoding="utf-8")
