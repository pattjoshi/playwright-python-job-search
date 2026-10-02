from unittest.mock import MagicMock

from job_search.models import Job
from job_search.scrapers.linkedin import LinkedInScraper, parse_search_results


def test_parse_search_results_reads_cards(page, fixture_html):
    page.set_content(fixture_html("linkedin_search.html"))

    jobs = parse_search_results(page)

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "linkedin"
    assert first.job_id == "4012345678"
    assert first.title == "Python Automation Engineer"
    assert first.company == "Acme Corp"
    assert first.location == "Bengaluru, Karnataka, India"
    assert first.url == "https://in.linkedin.com/jobs/view/python-automation-engineer-at-acme-4012345678"
    assert first.posted_text == "3 hours ago"
    assert first.hours_ago == 3
    assert jobs[1].hours_ago == 24


def test_fetch_description(browser, fixture_html):
    context = browser.new_context()
    html = fixture_html("linkedin_job.html")
    context.route("**/jobs-guest/jobs/api/jobPosting/*", lambda route: route.fulfill(body=html, content_type="text/html"))
    scraper = LinkedInScraper(context, delay_range=(0, 0))
    job = Job("linkedin", "4012345678", "Python Automation Engineer", "Acme", "Bengaluru", "url")

    scraper.fetch_description(job)

    assert job.description.startswith("About the role")
    assert "Playwright and pytest" in job.description
    context.close()


def test_search_paginates_and_uses_24h_filter(browser, fixture_html):
    context = browser.new_context()
    html = fixture_html("linkedin_search.html")
    requested = []

    def handle(route):
        requested.append(route.request.url)
        route.fulfill(body=html, content_type="text/html")

    context.route("**/jobs-guest/jobs/api/seeMoreJobPostings/search*", handle)
    scraper = LinkedInScraper(context, max_pages=3, delay_range=(0, 0))

    jobs = scraper.search("Python Developer", "Bengaluru")

    # Fixture has fewer than a full page of cards, so it stops after page 1.
    assert len(requested) == 1
    assert "f_TPR=r86400" in requested[0]
    assert "keywords=Python+Developer" in requested[0]
    assert len(jobs) == 2
    context.close()


def test_search_stops_on_http_error(browser):
    context = browser.new_context()
    context.route("**/seeMoreJobPostings/search*", lambda route: route.fulfill(status=429, body=""))
    scraper = LinkedInScraper(context, delay_range=(0, 0))
    scraper.pause = MagicMock()

    assert scraper.search("Python", "India") == []
    context.close()
