from job_search.models import Job
from job_search.pipeline import dedupe, filter_recent, keyword_score, matched_skills, shortlist_per_site
from job_search.utils import parse_relative_age


def make_job(job_id="1", title="Python Developer", company="Acme", location="Pune", source="linkedin", **kwargs):
    return Job(source=source, job_id=job_id, title=title, company=company, location=location, url="u", **kwargs)


def test_dedupe_same_id_and_same_role_on_other_board():
    jobs = [
        make_job("1"),
        make_job("1"),
        make_job("99", source="naukri", title="Python  Developer!", company="ACME"),
        make_job("2", title="SDET"),
    ]
    assert [job.job_id for job in dedupe(jobs)] == ["1", "2"]


def test_filter_recent_keeps_unknown_age():
    jobs = [make_job("1", hours_ago=3), make_job("2", hours_ago=48), make_job("3", hours_ago=None)]
    assert [job.job_id for job in filter_recent(jobs, 24)] == ["1", "3"]


def test_keyword_score_matches_whole_words():
    job = make_job(title="JavaScript Developer", description="React and Node.js")
    assert keyword_score(job, ["Java", "React"]) == 50
    assert keyword_score(job, []) == 0


def test_parse_relative_age():
    assert parse_relative_age("3 hours ago") == 3
    assert parse_relative_age("30 minutes ago") == 0.5
    assert parse_relative_age("1 day ago") == 24
    assert parse_relative_age("Posted 2 days ago") == 48
    assert parse_relative_age("30+ Days Ago") == 720
    assert parse_relative_age("Just posted") == 0
    assert parse_relative_age("Few Hours Ago") == 3
    assert parse_relative_age("") is None
    assert parse_relative_age("Reposted") is None


def test_matched_skills_whole_words():
    job = make_job(title="Python SDET", description="Playwright, pytest and JavaScript")
    assert matched_skills(job, ["Python", "pytest", "Java", "Selenium"]) == ["Python", "pytest"]


def test_shortlist_per_site_caps_each_site():
    jobs = [make_job(str(i), source="linkedin") for i in range(5)] + [make_job("n1", source="naukri", company="Other")]
    shortlist = shortlist_per_site(jobs, ["Python"], per_site=2)
    assert [job.source for job in shortlist].count("linkedin") == 2
    assert [job.source for job in shortlist].count("naukri") == 1
