import pytest

from job_search.history import JobHistory
from job_search.locations import is_remote, normalize_location
from job_search.models import Job
from job_search.pipeline import filter_experience
from job_search.scrapers.linkedin import experience_levels
from job_search.scrapers.naukri import search_url
from job_search.utils import experience_matches, parse_experience, parse_experience_option


def job(job_id, source="linkedin", **kwargs):
    return Job(source, job_id, f"Job {job_id}", "Co", "Pune", f"https://example.com/{job_id}", **kwargs)


def test_history_filters_and_marks_new(tmp_path):
    history = JobHistory(tmp_path / "data" / "history.sqlite3")
    history.record_seen([job("1"), job("2")])
    history.set_status("linkedin", "3", "applied")
    history.set_status("linkedin", "4", "hidden")

    jobs = [job(str(i)) for i in range(1, 6)]
    kept = history.filter(jobs, only_new=False)
    assert [(j.job_id, j.is_new) for j in kept] == [("1", False), ("2", False), ("5", True)]

    only_new = history.filter([job(str(i)) for i in range(1, 6)], only_new=True)
    assert [j.job_id for j in only_new] == ["5"]
    assert history.counts() == {"seen": 2, "applied": 1, "hidden": 1}


def test_history_status_changes_and_forget(tmp_path):
    history = JobHistory(tmp_path / "h.sqlite3")
    history.record_seen([job("1")])
    history.set_status("linkedin", "1", "applied")
    history.record_seen([job("1")])  # seeing it again doesn't undo "applied"
    assert history.statuses([job("1")]) == {("linkedin", "1"): "applied"}

    history.set_status("linkedin", "1", "seen")  # undo
    assert history.forget_seen() == 1
    assert history.counts()["seen"] == 0
    with pytest.raises(ValueError):
        history.set_status("linkedin", "1", "loved")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3-6 Yrs", (3, 6)),
        ("2 to 4 years", (2, 4)),
        ("Experience: 5 – 8 years", (5, 8)),
        ("We need 5+ years of Python", (5, 40)),
        ("Minimum 3 years experience", (3, 40)),
        ("Freshers welcome", (0, 1)),
        ("Great team, good pay", None),
        ("", None),
    ],
)
def test_parse_experience(text, expected):
    assert parse_experience(text) == expected


def test_experience_matches_overlap():
    assert experience_matches((3, 6), (1, 3))
    assert not experience_matches((5, 40), (1, 2))
    assert experience_matches(None, (1, 2))
    assert experience_matches((5, 8), None)


def test_parse_experience_option():
    assert parse_experience_option("1-2") == (1, 2)
    assert parse_experience_option("2 to 4") == (2, 4)
    assert parse_experience_option("3") == (3, 3)
    assert parse_experience_option("5-2") == (2, 5)
    for bad in ("senior", "1-2-3", "", "1-99"):
        with pytest.raises(ValueError):
            parse_experience_option(bad)


def test_filter_experience_keeps_unknown():
    jobs = [job("a", experience="1-3 Yrs"), job("b", experience="8-12 Yrs"), job("c"), job("d", description="Needs 7+ years")]
    assert [j.job_id for j in filter_experience(jobs, (1, 2))] == ["a", "c"]


def test_locations():
    assert normalize_location("Bangalore, Karnataka, India") == "Bengaluru"
    assert normalize_location("Gurgaon") == "Gurugram"
    assert normalize_location("Work from home") == "Remote"
    assert normalize_location("Pune, Maharashtra") == "Pune"
    assert normalize_location("  Berlin ") == "Berlin"
    assert is_remote("remote") and not is_remote("Pune")


def test_linkedin_experience_levels():
    assert experience_levels(0, 0) == [1, 2]
    assert experience_levels(1, 2) == [2, 3]
    assert experience_levels(1, 4) == [2, 3, 4]
    assert experience_levels(7, 9) == [4]


def test_naukri_url_with_remote_and_experience():
    url = search_url("Python Developer", "Remote", 1, 1, (2, 4))
    assert url == "https://www.naukri.com/python-developer-jobs?k=Python+Developer&jobAge=1&wfhType=2&experience=2"


def test_history_list_jobs(tmp_path):
    history = JobHistory(tmp_path / "h.sqlite3")
    history.set_status("naukri", "1", "applied", title="SDET", company="Acme", url="https://example.com/1")
    history.set_status("linkedin", "2", "applied", title="QA", company="Globex")
    history.set_status("linkedin", "3", "hidden", title="Dev")

    applied = history.list_jobs("applied")
    assert [job["job_id"] for job in applied] == ["2", "1"]  # most recent first
    assert applied[1]["title"] == "SDET" and applied[1]["company"] == "Acme"
    assert [job["job_id"] for job in history.list_jobs("hidden")] == ["3"]
    with pytest.raises(ValueError):
        history.list_jobs("loved")


def test_filter_experience_board_field_only():
    jobs = [job("a", experience="8-12 Yrs"), job("b", description="Needs 7+ years")]
    assert [j.job_id for j in filter_experience(jobs, (1, 2), use_description=False)] == ["b"]
