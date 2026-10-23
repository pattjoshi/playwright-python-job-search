"""Working through the auto-apply queue end to end: Answer Bank, tracker, limits, retry (local forms, real browser)."""

import threading

from job_search.models import Job
from tests.auto_apply_support import browser_factory, make_service
from tests.integration.form_site import form_site  # noqa: F401  (pytest fixture)


def job(job_id, apply_url, score=90, company="Acme"):
    return Job("linkedin", job_id, "QA Engineer", company, "Pune", f"https://www.linkedin.com/jobs/view/{job_id}",
               score=score, apply_url=apply_url, description="Python and Playwright test automation.")


def test_run_applies_tracks_and_waits_for_answers(tmp_path, form_site, browser):  # noqa: F811
    service = make_service(tmp_path, browser_factory(browser))
    service.answers.add_starters(1)
    for question, answer in [("Full name", "Om Prakash"), ("Email address", "om@example.com"), ("Phone number", "9876543210"),
                             ("Are you legally authorized to work in India?", "Yes")]:
        entry = service.answers.repo.find_by_key(1, question.lower().rstrip("?"))
        service.answers.update(1, entry["id"], {"answer": answer})
    service.save_settings(1, {"dry_run": False})
    question_count_before_run = service.answers.repo.counts(1)["needs_answer"] + 1  # + Gamma's required question
    queued = service.queue_jobs(1, [job("1", f"{form_site}/greenhouse.html"), job("2", f"{form_site}/unknown.html", 80, "Gamma"),
                                    job("3", f"{form_site}/x.html", score=50), job("4", "")])
    assert queued == 2  # under the minimum score, or no company link: not queued

    log = []
    assert service.run(1, threading.Event(), log.append) == 1
    jobs = {j["company"]: j for j in service.repo.for_user(1)}
    assert jobs["Acme"]["status"] == "submitted" and jobs["Acme"]["cover_letter"].startswith("Letter: QUESTION: Cover letter")
    letters = {a["question"] for a in jobs["Acme"]["answers"] if a["how"] == "ai_letter"}
    assert letters == {"Cover Letter", "Why do you want to join Acme?"}
    assert (tmp_path / "auto-apply" / f"{jobs['Acme']['id']}-cover-letter.docx").is_file()
    assert service.screenshot(1, jobs["Acme"]["id"]).is_file()
    tracked = service.applications.repo.for_user(1)
    assert [(a["company"], a["status"]) for a in tracked] == [("Acme", "applied")]

    gamma = jobs["Gamma"]
    assert gamma["status"] == "needs_answer" and "Kubernetes" in gamma["message"]
    question = service.answers.repo.find_by_key(1, "do you have experience with kubernetes in production")
    assert question["status"] == "needs_answer" and question["asked_by"] == "Gamma · QA Engineer" and question["options"] == ["Yes", "No"]
    assert any("Applying: QA Engineer at Gamma" in line for line in log)
    # Only the required unanswered question was added; optional ones without an answer (LinkedIn Profile) add nothing.
    assert service.answers.repo.counts(1)["needs_answer"] == question_count_before_run

    service.answers.update(1, question["id"], {"answer": "No"})  # you answer it once in the Answer Bank...
    service.retry(1, gamma["id"])
    assert service.run(1, threading.Event()) == 1  # ...and it goes through
    assert service.repo.get(1, gamma["id"])["status"] == "submitted"


def test_dry_run_and_daily_limit(tmp_path, form_site, browser):  # noqa: F811
    service = make_service(tmp_path, browser_factory(browser))
    service.answers.create(1, {"question": "Full name", "answer": "Om Prakash"})
    service.answers.create(1, {"question": "Email", "answer": "om@example.com"})
    service.answers.create(1, {"question": "Are you legally authorized to work in India?", "answer": "Yes"})
    service.save_settings(1, {"daily_limit": 1})  # dry run is on by default
    service.queue_jobs(1, [job("1", f"{form_site}/greenhouse.html?a", 95), job("2", f"{form_site}/greenhouse.html?b", 90)])

    assert service.run(1, threading.Event()) == 1
    statuses = {j["source_job_id"]: j["status"] for j in service.repo.for_user(1)}
    assert statuses == {"1": "filled", "2": "queued"}  # best match first; the limit stops the rest
    assert service.applications.repo.for_user(1) == []  # a dry run applies to nothing
    said = []
    assert service.run(1, threading.Event(), said.append) == 0 and "limit of 1" in said[0]
