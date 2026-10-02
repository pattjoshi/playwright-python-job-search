import json

from job_search.models import Job
from job_search.scrapers import indeed, naukri
from job_search.scrapers.indeed import IndeedScraper
from job_search.scrapers.naukri import NaukriScraper, parse_api_jobs, search_url


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


def test_naukri_search_reads_api_response(browser, fixture_html):
    context = browser.new_context()
    api_json = fixture_html("naukri_api.json")
    page_html = "<html><body><script>fetch('/jobapi/v3/search?noOfResults=20')</script></body></html>"
    context.route("**/jobapi/v3/search*", lambda route: route.fulfill(body=api_json, content_type="application/json"))
    context.route("**/python-developer-jobs-in-bengaluru*", lambda route: route.fulfill(body=page_html, content_type="text/html"))

    jobs = NaukriScraper(context, delay_range=(0, 0)).search("Python Developer", "Bengaluru")

    assert [job.job_id for job in jobs] == ["021025012345", "021025067890"]
    context.close()


def test_naukri_falls_back_to_page_cards(browser, fixture_html, monkeypatch):
    monkeypatch.setattr(naukri, "API_PATH", "/never-called")
    context = browser.new_context()
    html = fixture_html("naukri_search.html")
    context.route("**/qa-jobs*", lambda route: route.fulfill(body=html, content_type="text/html"))
    scraper = NaukriScraper(context, delay_range=(0, 0))
    # Don't wait 20s for an API call that never comes.
    original = scraper.page.expect_response
    scraper.page.expect_response = lambda predicate, timeout: original(predicate, timeout=500)

    jobs = scraper.search("QA", "")

    assert len(jobs) == 1
    job = jobs[0]
    assert (job.job_id, job.title, job.company, job.location) == ("021025099999", "QA Engineer", "Initech", "Hyderabad")
    assert job.hours_ago == 48
    assert job.description == "Manual and automation testing for web apps.\nSkills: Selenium, Java"
    context.close()


def test_indeed_parse_and_search(browser, fixture_html):
    context = browser.new_context()
    html = fixture_html("indeed_search.html")
    requested = []

    def handle(route):
        requested.append(route.request.url)
        route.fulfill(body=html, content_type="text/html")

    context.route("**/in.indeed.com/jobs*", handle)
    jobs = IndeedScraper(context, max_pages=3, delay_range=(0, 0)).search("Python Developer", "Bengaluru")

    # Page 2 returns the same job again, so the search stops there.
    assert len(requested) == 2
    assert "fromage=1" in requested[0] and "sort=date" in requested[0]
    assert len(jobs) == 1
    job = jobs[0]
    assert (job.job_id, job.title, job.company, job.location) == (
        "a1b2c3d4e5f6", "Python Developer", "Umbrella Corp", "Bengaluru, Karnataka"
    )
    assert job.url == "https://in.indeed.com/viewjob?jk=a1b2c3d4e5f6"
    assert (job.posted_text, job.hours_ago) == ("5 hours ago", 5)
    assert "Django" in job.description
    context.close()


def test_indeed_bot_check_is_skipped(browser, monkeypatch):
    monkeypatch.setattr(indeed, "CARD", "div.never")
    context = browser.new_context()
    page = "<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>"
    context.route("**/in.indeed.com/jobs*", lambda route: route.fulfill(body=page, content_type="text/html"))
    scraper = IndeedScraper(context, delay_range=(0, 0))
    original = scraper.page.wait_for_selector
    scraper.page.wait_for_selector = lambda selector, timeout: original(selector, timeout=200)

    assert scraper.search("Python", "India") == []
    context.close()


def test_indeed_fetch_description(browser):
    context = browser.new_context()
    page = '<div id="jobDescriptionText"><p>Own our Playwright test suite.</p></div>'
    context.route("**/viewjob*", lambda route: route.fulfill(body=page, content_type="text/html"))
    job = Job("indeed", "x1", "QA", "Co", "Pune", "https://in.indeed.com/viewjob?jk=x1")

    IndeedScraper(context, delay_range=(0, 0)).fetch_description(job)

    assert job.description == "Own our Playwright test suite."
    context.close()


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
