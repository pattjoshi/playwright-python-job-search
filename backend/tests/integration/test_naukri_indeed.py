from job_search.models import Job
from job_search.services.scraping import indeed, naukri
from job_search.services.scraping.indeed import IndeedScraper
from job_search.services.scraping.naukri import NaukriScraper


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
    assert job.apply_url == ""
    context.close()


def test_indeed_fetch_description_finds_company_apply_link(browser):
    context = browser.new_context()
    page = ('<div id="jobDescriptionText"><p>QA role</p></div>'
            '<div id="applyButtonLinkContainer"><a href="/rc/clk?jk=x1&amp;from=vj">Apply on company site</a></div>')
    context.route("**/viewjob*", lambda route: route.fulfill(body=page, content_type="text/html"))
    job = Job("indeed", "x1", "QA", "Co", "Pune", "https://in.indeed.com/viewjob?jk=x1")

    IndeedScraper(context, delay_range=(0, 0)).fetch_description(job)

    assert job.apply_url == "https://in.indeed.com/rc/clk?jk=x1&from=vj"
    context.close()
