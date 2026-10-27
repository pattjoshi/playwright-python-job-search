import re
import time

from job_search.models import Job
from job_search.services.scraping import indeed, naukri
from job_search.services.scraping.indeed import IndeedScraper
from job_search.services.scraping.naukri import NaukriScraper
from job_search.services.search.sites import collect_site

HOME = "https://www.naukri.com/"


def naukri_context(browser, visits=None):
    """A context whose Naukri home page (opened once before searching) is a local stub."""
    context = browser.new_context()
    context.route(HOME, lambda route: (visits is not None and visits.append(1),
                                       route.fulfill(body="<title>Naukri</title>", content_type="text/html")))
    return context


def test_naukri_search_reads_api_response(browser, fixture_html):
    visits = []
    context = naukri_context(browser, visits)
    api_json = fixture_html("naukri_api.json")
    page_html = "<html><body><script>fetch('/jobapi/v3/search?noOfResults=20')</script></body></html>"
    context.route("**/jobapi/v3/search*", lambda route: route.fulfill(body=api_json, content_type="application/json"))
    context.route("**/python-developer-jobs-in-bengaluru*", lambda route: route.fulfill(body=page_html, content_type="text/html"))

    jobs = NaukriScraper(context, delay_range=(0, 0)).search("Python Developer", "Bengaluru")

    assert [job.job_id for job in jobs] == ["021025012345", "021025067890"]
    assert visits == [1]  # the home page first, like a person
    context.close()


def test_naukri_falls_back_to_page_cards(browser, fixture_html, monkeypatch):
    monkeypatch.setattr(naukri, "API_PATH", re.compile("/never-called"))
    monkeypatch.setattr(naukri, "API_WAIT_S", 0.5)  # don't wait 20s for an API call that never comes
    context = naukri_context(browser)
    html = fixture_html("naukri_search.html")
    context.route("**/qa-jobs*", lambda route: route.fulfill(body=html, content_type="text/html"))
    jobs = NaukriScraper(context, delay_range=(0, 0)).search("QA", "")

    assert len(jobs) == 1
    job = jobs[0]
    assert (job.job_id, job.title, job.company, job.location) == ("021025099999", "QA Engineer", "Initech", "Hyderabad")
    assert job.hours_ago == 48
    assert job.description == "Manual and automation testing for web apps.\nSkills: Selenium, Java"
    context.close()


def test_naukri_access_denied_stops_the_site_at_once(browser):
    context = naukri_context(browser)
    denied = "<html><head><title>Access Denied</title></head><body>You don't have permission</body></html>"
    requested = []
    context.route("**/*-jobs*", lambda route: (requested.append(1), route.fulfill(body=denied, status=403, content_type="text/html")))
    scraper = NaukriScraper(context, delay_range=(0, 0))
    events = []

    started = time.monotonic()
    jobs = collect_site(scraper, "naukri", ["AI Engineer", "LLM Engineer"], ["Pune", "Remote"], lambda *a, **k: events.append(k))

    assert jobs == [] and scraper.blocked
    assert len(requested) == 1  # the other three searches are skipped, not refused one by one
    assert time.monotonic() - started < 10  # no 20s wait for results that never come
    assert events[-1] == {"site": "naukri", "status": "blocked", "found": 0}
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
