"""Board Easy Apply through the auto-apply queue: switches, logins, per-board limits (saved pages, real browser)."""

import threading

from job_search.models import Job
from tests.auto_apply_support import browser_factory, make_service
from tests.integration.form_site import form_site  # noqa: F401  (pytest fixture)

LOGINS = {"naukri": ("om@example.com", "right-password"), "linkedin": ("om@example.com", "right-password")}


def board_job(source, job_id, url, score=90):
    return Job(source, job_id, "SDET", f"{source.title()} Co {job_id}", "Pune", url, score=score)


def test_boards_queue_only_when_turned_on(tmp_path, form_site):  # noqa: F811
    service = make_service(tmp_path)
    jobs = [board_job("naukri", "1", f"{form_site}/naukri_job.html")]
    assert service.queue_jobs(1, jobs) == 0  # every board is off until you turn it on
    service.save_settings(1, {"naukri": True})
    assert service.queue_jobs(1, jobs) == 1
    assert service.repo.for_user(1)[0]["platform"] == "naukri"


def test_run_signs_in_applies_and_respects_board_limits(tmp_path, form_site, browser):  # noqa: F811
    service = make_service(tmp_path, browser_factory(browser), board_logins=LOGINS, pace=0, board_base_url=form_site)
    for question, answer in [("Are you willing to relocate to Bengaluru?", "Yes"), ("What is your notice period?", "30 days"),
                             ("Mobile phone number", "9876543210"),
                             ("How many years of work experience do you have with Python?", "3")]:
        service.answers.create(1, {"question": question, "answer": answer})
    service.save_settings(1, {"naukri": True, "linkedin": True, "indeed": True, "dry_run": False, "board_daily_limit": 1})
    service.queue_jobs(1, [
        board_job("naukri", "1", f"{form_site}/naukri_job.html", 95), board_job("naukri", "2", f"{form_site}/naukri_job.html?2", 94),
        board_job("linkedin", "3", f"{form_site}/linkedin_job.html", 93), board_job("indeed", "4", f"{form_site}/indeed_job.html", 92),
    ])

    log = []
    assert service.run(1, threading.Event(), log.append) == 2
    status = {j["source_job_id"]: (j["status"], j["message"]) for j in service.repo.for_user(1)}
    assert status["1"][0] == "submitted" and status["3"][0] == "submitted"
    assert status["2"][0] == "queued"  # Naukri's limit of 1 a day is reached: it waits for tomorrow
    assert status["4"][0] == "blocked" and "INDEED_EMAIL" in status["4"][1]  # no Indeed login in .env
    tracked = {a["company"] for a in service.applications.repo.for_user(1)}
    assert tracked == {"Naukri Co 1", "Linkedin Co 3"}
    assert service.overview(1)["boards"]["naukri"] == {"today": 1, "has_login": True}
    assert service.overview(1)["boards"]["indeed"]["has_login"] is False
