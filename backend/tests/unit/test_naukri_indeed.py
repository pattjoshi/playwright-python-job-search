import json

from job_search.services.scraping.naukri import parse_api_jobs, search_url


def test_naukri_search_url():
    assert search_url("Python Developer", "Bengaluru", 1, 1) == (
        "https://www.naukri.com/python-developer-jobs-in-bengaluru?k=Python+Developer&jobAge=1&l=Bengaluru"
    )
    assert search_url("SDET", "", 2, 3) == "https://www.naukri.com/sdet-jobs-2?k=SDET&jobAge=3"


def test_naukri_parse_api_jobs(fixture_html):
    jobs = parse_api_jobs(json.loads(fixture_html("naukri_api.json")))

    assert len(jobs) == 2
    first = jobs[0]
    assert (first.source, first.job_id, first.title, first.company) == (
        "naukri", "021025012345", "Python Automation Engineer", "Acme Technologies"
    )
    assert first.location == "Bengaluru"
    assert first.url.startswith("https://www.naukri.com/job-listings-python-automation-engineer")
    assert first.hours_ago == 3
    assert first.description == "Build UI & API automation with Python .\nSkills: Python, Playwright, Selenium, API Testing"
    assert jobs[1].url == "https://www.naukri.com/job-listings-sdet-globex-pune-021025067890"
    assert jobs[1].hours_ago == 24


def test_naukri_label_wins_over_old_created_date():
    # A job reposted today: label says "Just Now" but createdDate is 30 days old.
    old = 1_000 * 60 * 60 * 24 * 30
    import time as _time

    data = {"jobDetails": [{"title": "SDET", "jobId": "1234567", "footerPlaceholderLabel": "Just Now",
                            "createdDate": _time.time() * 1000 - old}]}
    assert parse_api_jobs(data)[0].hours_ago == 0

    # No usable label: fall back to createdDate.
    data["jobDetails"][0]["footerPlaceholderLabel"] = ""
    assert round(parse_api_jobs(data)[0].hours_ago) == 720
