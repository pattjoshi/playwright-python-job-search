"""Finding the company's application page behind a board's "Apply on company site" link."""

from job_search.models import Job
from job_search.repositories import CacheRepository
from job_search.services.scraping.apply_links import external_apply_url
from job_search.services.scraping.naukri import parse_api_jobs

LINKEDIN = ("linkedin.com",)


def test_linkedin_hidden_link_is_unwrapped():
    comment = ('<!--"https://www.linkedin.com/jobs/view/externalApply/4012345678?url=https%3A%2F%2Fboards%2Egreenhouse%2Eio'
               '%2Facme%2Fjobs%2F123%3Fgh_src%3Dli&amp;urlHash=AbCd"-->')
    assert external_apply_url(comment, board_hosts=LINKEDIN) == "https://boards.greenhouse.io/acme/jobs/123?gh_src=li"
    # Without a target it's LinkedIn's own flow, not a company page.
    assert external_apply_url('"https://www.linkedin.com/jobs/view/externalApply/1"', board_hosts=LINKEDIN) == ""


def test_other_links():
    assert external_apply_url("/rc/clk?jk=x1&from=vj", "https://in.indeed.com", ("indeed.com",)) == "https://in.indeed.com/rc/clk?jk=x1&from=vj"
    assert external_apply_url("https://jobs.lever.co/acme/abc", board_hosts=("naukri.com",)) == "https://jobs.lever.co/acme/abc"
    assert external_apply_url("javascript:void(0)") == "" and external_apply_url("") == ""


def test_naukri_company_site_jobs_and_cache(tmp_path):
    jobs = parse_api_jobs({"jobDetails": [
        {"jobId": "1", "title": "SDET", "companyName": "Acme", "applyRedirectUrl": "https://acme.example/careers/1"},
        {"jobId": "2", "title": "QA", "companyName": "Beta"},
    ]})
    assert [job.apply_url for job in jobs] == ["https://acme.example/careers/1", ""]

    cache = CacheRepository(tmp_path / "cache.sqlite3")
    cache.save_descriptions([Job("linkedin", "9", "SDET", "Acme", "Pune", "u", description="d", apply_url="https://x.test/apply")])
    again = Job("linkedin", "9", "SDET", "Acme", "Pune", "u")
    assert cache.fill_descriptions([again]) == [] and again.apply_url == "https://x.test/apply"
