"""Filling and submitting saved copies of career-page forms in a real (headless) browser."""

import pytest

from job_search.services.auto_apply.applier import apply_one
from job_search.services.auto_apply.filler import Filler, pick
from job_search.services.auto_apply.service import write_docx
from tests.integration.form_site import form_site  # noqa: F401  (pytest fixture)

ANSWERS = {
    "Full name": "Om Prakash", "Email": "om@example.com", "Phone": "9876543210", "LinkedIn Profile": "https://linkedin.com/in/om",
    "Are you legally authorized to work in India?": "Yes", "Are you willing to relocate?": "Yes",
    "How soon can you join us?": "30 days", "I agree to the privacy policy": "Yes",
}


@pytest.fixture
def make_filler(tmp_path):
    resume = tmp_path / "cv.pdf"
    resume.write_bytes(b"%PDF-1.4 resume")

    def make(answers=ANSWERS):
        return Filler(lambda question, options, required: (answers.get(question), "saved"), lambda question: f"Letter for: {question}",
                      resume, lambda text: write_docx(tmp_path / "cover.docx", text))
    return make


@pytest.fixture
def page(browser):
    context = browser.new_context()
    yield context.new_page()
    context.close()


def test_pick_matches_options():
    assert pick(["Yes", "No"], "yes") == "Yes" and pick(["Yes", "No"], "No") == "No"
    assert pick(["Not sure", "No"], "No") == "No"  # not "Not sure"
    assert pick(["Immediately", "30 days", "60 days"], "30") == "30 days"
    assert pick(["Yes, I am authorized", "No"], "Yes") == "Yes, I am authorized"
    assert pick(["Remote", "Office"], "Hybrid") is None and pick(["A"], "") is None


def test_dry_run_fills_a_greenhouse_style_form(page, make_filler, form_site, tmp_path):  # noqa: F811
    filler = make_filler()
    outcome = apply_one(page, f"{form_site}/greenhouse.html", filler, dry_run=True, screenshot=tmp_path / "shot.png")

    assert outcome.status == "filled" and outcome.screenshot == "shot.png" and (tmp_path / "shot.png").stat().st_size > 0
    assert page.input_value("#first_name") == "Om" and page.input_value("#last_name") == "Prakash"
    assert page.input_value("#email") == "om@example.com" and page.input_value("#q2") == "1"  # "Yes"
    assert page.input_value("#q3") == "Letter for: Why do you want to join Acme?"
    assert page.evaluate("document.querySelector('#resume').files[0].name") == "cv.pdf"
    assert page.evaluate("document.querySelector('#cover_letter').files[0].name") == "cover.docx"
    assert page.input_value("[name=newsletter]") == ""  # outside the application form
    how = {a["question"]: a["how"] for a in outcome.answers}
    assert how["Resume/CV"] == "resume" and how["Cover Letter"] == "ai_letter" and filler.cover_letter == "Letter for: Cover letter"
    shown = {a["question"]: a["answer"] for a in outcome.answers}
    assert shown["Resume/CV"] == "Your resume file" and shown["Cover Letter"] == "Cover letter written by AI (Word file)"
    assert page.url.endswith("/greenhouse.html")  # not submitted


def test_submits_and_sees_the_confirmation(page, make_filler, form_site, tmp_path):  # noqa: F811
    outcome = apply_one(page, f"{form_site}/greenhouse.html", make_filler(), dry_run=False, screenshot=tmp_path / "s.png")
    assert (outcome.status, outcome.message) == ("submitted", "Submitted.")
    assert "Thank you for applying" in page.content()


def test_clicks_apply_then_fills_a_lever_style_form(page, make_filler, form_site, tmp_path):  # noqa: F811
    outcome = apply_one(page, f"{form_site}/lever_job.html", make_filler(), dry_run=False, screenshot=tmp_path / "s.png")
    assert outcome.status == "submitted", outcome.message
    answered = {a["question"]: a["answer"] for a in outcome.answers}
    assert answered["Full name"] == "Om Prakash" and answered["Are you willing to relocate?"] == "Yes"
    assert answered["How soon can you join us?"] == "30 days" and answered["I agree to the privacy policy"] == "Yes"
    assert "relocate=yes" in page.url and "consent=on" in page.url


def test_required_question_without_an_answer_is_not_submitted(page, make_filler, form_site, tmp_path):  # noqa: F811
    outcome = apply_one(page, f"{form_site}/unknown.html", make_filler(), dry_run=False, screenshot=tmp_path / "s.png")
    assert outcome.status == "needs_answer"
    assert outcome.message == "Waiting for your answer to: Do you have experience with Kubernetes in production?"
    assert page.url.endswith("/unknown.html") and outcome.screenshot == "s.png"


@pytest.mark.parametrize(("name", "status", "message"), [
    ("login.html", "blocked", "sign in"),
    ("thanks.html", "failed", "Couldn't find an application form"),
    ("invalid.html", "failed", "Your phone number is invalid."),
])
def test_pages_it_cannot_finish(page, make_filler, form_site, tmp_path, name, status, message):  # noqa: F811
    outcome = apply_one(page, f"{form_site}/{name}", make_filler(), dry_run=False, screenshot=tmp_path / "s.png", confirm_s=2)
    assert outcome.status == status and message in outcome.message


def test_accounts_only_systems_are_skipped(page, make_filler, tmp_path):
    outcome = apply_one(page, "https://acme.wd5.myworkdayjobs.com/en-US/careers/job/1", make_filler(), True, tmp_path / "s.png")
    assert outcome.status == "blocked" and "Workday needs an account" in outcome.message
