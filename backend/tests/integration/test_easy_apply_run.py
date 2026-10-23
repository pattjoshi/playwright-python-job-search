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
    assert service.overview(1)["boards"]["naukri"] == {"today": 1, "has_login": True, "signed_in": True}
    assert service.overview(1)["boards"]["indeed"]["has_login"] is False


def test_one_tab_for_the_whole_run_try_this_job_and_saved_pages(tmp_path, form_site, browser):  # noqa: F811
    """A visible browser quits when its last tab closes, so the run keeps its tab; failures keep the page."""
    seen = []

    from contextlib import contextmanager

    @contextmanager
    def tracked(_headless):
        context = browser.new_context()
        context.on("page", lambda page: seen.append(page))
        try:
            yield context
        finally:
            context.close()

    service = make_service(tmp_path, tracked, pace=0, board_base_url=form_site, board_logins=LOGINS)
    service.save_settings(1, {"linkedin": True, "dry_run": True})
    service.answers.create(1, {"question": "Mobile phone number", "answer": "9876543210"})
    service.answers.create(1, {"question": "How many years of work experience do you have with Python?", "answer": "3"})
    service.queue_jobs(1, [board_job("linkedin", "1", f"{form_site}/linkedin_job_signed_out.html", 95),
                           board_job("linkedin", "2", f"{form_site}/linkedin_job.html", 90)])
    assert service.run(1, threading.Event()) == 0
    jobs = {j["source_job_id"]: j for j in service.overview(1)["jobs"]}
    assert jobs["1"]["status"] == "blocked" and "Not signed in" in jobs["1"]["message"] and jobs["1"]["has_page"]
    assert jobs["2"]["status"] == "queued"  # LinkedIn says you're signed out: its other jobs wait
    assert "<h1>QA Engineer</h1>" in service.saved_page(1, jobs["1"]["id"]).read_text()  # the job page, as it was
    assert len(seen) == 1  # sign-in and the job used the same tab

    tried = service.run(1, threading.Event(), only_job=jobs["2"]["id"])  # "Try this job"
    assert tried == 1, service.repo.get(1, jobs["2"]["id"])["message"]
    assert service.repo.get(1, jobs["2"]["id"])["status"] == "filled"


def test_sign_in_yourself_is_remembered(tmp_path, form_site, browser):  # noqa: F811
    service = make_service(tmp_path, browser_factory(browser), pace=0, board_base_url=form_site,
                           board_logins={"naukri": ("om@example.com", "right-password")})
    assert service.overview(1)["boards"]["naukri"]["signed_in"] is False
    assert service.sign_in("naukri") is None
    assert service.overview(1)["boards"]["naukri"]["signed_in"] is True
