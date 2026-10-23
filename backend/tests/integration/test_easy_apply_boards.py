"""Easy Apply on saved copies of Naukri, LinkedIn and Indeed pages (local server, real headless browser)."""

import pytest

from job_search.services.auto_apply.boards import BOARDS
from job_search.services.auto_apply.filler import Filler
from tests.integration.form_site import form_site  # noqa: F401  (pytest fixture)

LOGIN = ("om@example.com", "right-password")
ANSWERS = {
    "Are you willing to relocate to Bengaluru?": "Yes", "What is your notice period?": "30 days",
    "Mobile phone number": "9876543210", "How many years of work experience do you have with Python?": "3",
    "Full name": "Om Prakash", "Email": "om@example.com", "Are you legally authorized to work in India?": "Yes",
}


@pytest.fixture
def page(browser):
    context = browser.new_context()  # a fresh "profile": not signed in
    yield context.new_page()
    context.close()


def filler(tmp_path, answers=ANSWERS):
    return Filler(lambda question, options, required: (answers.get(question), "saved"), None, tmp_path / "cv.pdf", lambda t: t)


def board(name, site, wait_s=0):
    return BOARDS[name](pace=0, wait_for_you_s=wait_s, base_url=site)


@pytest.mark.parametrize("name", ["naukri", "linkedin", "indeed"])
def test_sign_in_once_then_stay_signed_in(page, form_site, name):  # noqa: F811
    site = board(name, form_site)
    problem = site.ensure_login(page, None)
    assert problem.startswith("Not signed in") and f"{name.upper()}_EMAIL" in problem
    assert "Couldn't sign in" in site.ensure_login(page, ("om@example.com", "wrong"))
    assert site.ensure_login(page, LOGIN) is None
    assert site.ensure_login(page, None) is None  # the saved profile is still signed in: no password needed


def test_naukri_chat_questions(page, form_site, tmp_path):  # noqa: F811
    naukri = board("naukri", form_site)
    dry = naukri.apply(page, f"{form_site}/naukri_job.html", filler(tmp_path), True, tmp_path / "s.png")
    assert dry.status == "filled" and "nothing was clicked" in dry.message
    outcome = naukri.apply(page, f"{form_site}/naukri_job.html", filler(tmp_path), False, tmp_path / "s.png")
    assert outcome.status == "submitted"
    assert page.evaluate("window.given") == ["Yes", "30 days"]
    assert [a["question"] for a in outcome.answers] == ["Are you willing to relocate to Bengaluru?", "What is your notice period?"]


def test_naukri_unknown_question_and_company_site(page, form_site, tmp_path):  # noqa: F811
    naukri = board("naukri", form_site)
    outcome = naukri.apply(page, f"{form_site}/naukri_job.html", filler(tmp_path, {}), False, tmp_path / "s.png")
    assert outcome.status == "needs_answer" and "relocate to Bengaluru" in outcome.message
    company = naukri.apply(page, f"{form_site}/naukri_company.html", filler(tmp_path), False, tmp_path / "s.png")
    assert company.status == "blocked" and "company's site" in company.message


def test_linkedin_steps_dry_run_discards_and_live_submits(page, form_site, tmp_path):  # noqa: F811
    linkedin = board("linkedin", form_site)
    dry = linkedin.apply(page, f"{form_site}/linkedin_job.html", filler(tmp_path), True, tmp_path / "s.png")
    assert dry.status == "filled" and page.evaluate("window.discarded") is True
    assert page.evaluate("[window.v0, window.v1]") == ["9876543210", "3"]
    live = linkedin.apply(page, f"{form_site}/linkedin_job.html", filler(tmp_path), False, tmp_path / "s.png")
    assert (live.status, live.message) == ("submitted", "Submitted.")


def test_linkedin_bad_answer_shows_the_form_error(page, form_site, tmp_path):  # noqa: F811
    answers = {**ANSWERS, "How many years of work experience do you have with Python?": "three"}
    outcome = board("linkedin", form_site).apply(page, f"{form_site}/linkedin_job.html", filler(tmp_path, answers), False,
                                                 tmp_path / "s.png")
    assert outcome.status == "failed" and "Enter a whole number" in outcome.message


def test_indeed_new_tab_steps(page, form_site, tmp_path):  # noqa: F811
    outcome = board("indeed", form_site).apply(page, f"{form_site}/indeed_job.html", filler(tmp_path), False, tmp_path / "s.png")
    assert outcome.status == "submitted"
    assert {a["question"] for a in outcome.answers} >= {"Full name", "Email", "Are you legally authorized to work in India?"}


def test_sign_in_yourself_without_a_password(page, form_site):  # noqa: F811
    """No password in .env: with the browser open, the app waits while you log in yourself."""
    page.context.add_init_script("setTimeout(() => document.querySelectorAll('form').forEach((f) => f.remove()), 1500)")
    assert board("linkedin", form_site, wait_s=10).ensure_login(page, None) is None


def test_linkedin_waits_for_a_late_button_and_spots_signed_out_pages(page, form_site, tmp_path):  # noqa: F811
    linkedin = board("linkedin", form_site)
    late = linkedin.apply(page, f"{form_site}/linkedin_job_slow.html", filler(tmp_path), True, tmp_path / "s.png")
    assert late.status == "filled"  # the Easy Apply button appeared after the page loaded
    out = linkedin.apply(page, f"{form_site}/linkedin_job_signed_out.html", filler(tmp_path), True, tmp_path / "s.png")
    assert out.status == "blocked" and out.message.startswith("Not signed in to LinkedIn") and out.stop_platform


def test_linkedin_opens_the_signed_in_job_page():
    from job_search.services.auto_apply.boards.linkedin import job_page_url

    assert job_page_url("https://in.linkedin.com/jobs/view/ai-engineer-at-straive-4012345678") == \
        "https://www.linkedin.com/jobs/view/4012345678/"
    assert job_page_url("https://www.linkedin.com/jobs/view/4012345678") == "https://www.linkedin.com/jobs/view/4012345678/"
    assert job_page_url("http://127.0.0.1:9/linkedin_job.html") == "http://127.0.0.1:9/linkedin_job.html"
