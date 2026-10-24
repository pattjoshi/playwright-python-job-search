"""The Chrome extension end to end: the real app on a local port, the extension in Chromium, saved board pages.

Uses the popup like a person (address, key, Start) and checks every job is applied to and reported back.
"""

import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from job_search.api.app import create_app
from job_search.config import Settings
from job_search.models import Job
from tests.integration.form_site import FORMS

EXTENSION = Path(__file__).parents[3] / "extension"
ANSWERS = {
    "Mobile phone number": "9876543210", "How many years of work experience do you have with Python?": "3",
    "Are you willing to relocate to Bengaluru?": "Yes", "What is your notice period?": "30 days",
    "Full name": "Om Prakash", "Email": "om@example.com", "Are you legally authorized to work in India?": "Yes",
}


@pytest.fixture
def app_server(tmp_path):
    app = create_app(Settings(openai_api_key=None, history_path=tmp_path / "h.sqlite3"), output_dir=tmp_path / "out",
                     upload_dir=tmp_path / "up", frontend_dir=tmp_path / "front", answer_ai=lambda: None)
    app.router.routes.insert(0, Mount("/test-forms", app=StaticFiles(directory=FORMS)))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield app.state.context, f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_extension_applies_in_its_own_chrome(app_server):
    ctx, base = app_server
    ctx.auth.users.create("om@example.com", "Om", "x", "owner")
    service = ctx.auto_apply.service
    for question, answer in ANSWERS.items():
        service.answers.create(1, {"question": question, "answer": answer})
    service.save_settings(1, {"linkedin": True, "naukri": True, "indeed": True, "dry_run": False, "min_score": 0})
    forms = f"{base}/test-forms"
    service.queue_jobs(1, [Job("linkedin", "1", "QA Engineer", "Acme", "Pune", f"{forms}/linkedin_job.html", score=95),
                           Job("naukri", "2", "SDET", "Beta", "Pune", f"{forms}/naukri_job.html", score=90),
                           Job("indeed", "3", "SDET", "Gamma", "Pune", f"{forms}/indeed_job.html", score=85)])
    log = run_extension(ctx, base, "Connected as Om · 3 waiting · LIVE")

    jobs = {j["company"]: j for j in service.repo.for_user(1)}
    assert {name: j["status"] for name, j in jobs.items()} == {"Acme": "submitted", "Beta": "submitted", "Gamma": "submitted"}, log
    assert {a["question"] for a in jobs["Beta"]["answers"]} == {"Are you willing to relocate to Bengaluru?", "What is your notice period?"}
    assert any(a["question"] == "Are you legally authorized to work in India?" for a in jobs["Gamma"]["answers"])
    assert service.screenshot(1, jobs["Acme"]["id"]) is not None  # captured in Chrome
    assert {a["company"] for a in service.applications.repo.for_user(1)} == {"Acme", "Beta", "Gamma"}
    assert service.overview(1)["boards"]["linkedin"]["signed_in"] is True


def run_extension(ctx, base, waiting_text):
    """Connect the extension with a key in its popup, press Start, wait until the queue is done; returns the log.

    Runs on its own thread: the suite's shared browser already uses Playwright on the test's thread.
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_run_extension, ctx, base, waiting_text).result()


def _run_extension(ctx, base, waiting_text):
    service, key = ctx.auto_apply.service, ctx.extension_keys.create(1)
    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            tempfile.mkdtemp(), headless=False, executable_path=os.getenv("CHROMIUM_EXECUTABLE") or None,
            args=["--headless=new", f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
        )
        worker = browser.service_workers[0] if browser.service_workers else browser.wait_for_event("serviceworker")
        popup = browser.new_page()
        popup.goto(worker.url.replace("background.js", "popup.html"))
        popup.evaluate("chrome.storage.local.set({settings: {pace: 0}})")  # no human-like pauses in tests
        popup.reload()
        popup.get_by_label("App address").fill(base)
        popup.get_by_label("Key").fill(key)
        popup.get_by_role("button", name="Save and test").click()
        expect(popup.get_by_role("status")).to_contain_text(waiting_text)
        popup.get_by_role("button", name="Start").click()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and any(j["status"] in ("queued", "running") for j in service.repo.for_user(1)):
            time.sleep(0.5)
        expect(popup.get_by_label("Log")).to_contain_text("Nothing waiting", timeout=10_000)  # the run ended by itself
        expect(popup.get_by_role("button", name="Start")).to_be_enabled()
        log = popup.get_by_label("Log").inner_text()
        browser.close()
    return log


def test_extension_dry_run_unknown_question_and_signed_out(app_server):
    ctx, base = app_server
    ctx.auth.users.create("om@example.com", "Om", "x", "owner")
    service = ctx.auto_apply.service
    for question in ("Mobile phone number", "How many years of work experience do you have with Python?"):
        service.answers.create(1, {"question": question, "answer": ANSWERS[question]})
    service.save_settings(1, {"linkedin": True, "naukri": True, "min_score": 0, "dry_run": False})
    forms = f"{base}/test-forms"
    service.queue_jobs(1, [Job("linkedin", "1", "QA", "Acme", "Pune", f"{forms}/linkedin_job_signed_out.html", score=95),
                           Job("naukri", "2", "SDET", "Beta", "Pune", f"{forms}/naukri_job.html", score=90)])
    log = run_extension(ctx, base, "2 waiting")
    jobs = {j["company"]: j for j in service.repo.for_user(1)}
    assert jobs["Acme"]["status"] == "blocked" and "Not signed in to LinkedIn" in jobs["Acme"]["message"], log
    assert jobs["Acme"]["has_page"] if "has_page" in jobs["Acme"] else service.saved_page(1, jobs["Acme"]["id"]) is not None
    assert jobs["Beta"]["status"] == "needs_answer" and "relocate to Bengaluru" in jobs["Beta"]["message"]
    asked = service.answers.repo.find_by_key(1, "are you willing to relocate to bengaluru")
    assert asked["status"] == "needs_answer" and asked["asked_by"] == "Beta · SDET"

    service.save_settings(1, {"dry_run": True})
    service.retry(1, jobs["Acme"]["id"])
    service.repo.update(1, jobs["Acme"]["id"], {"apply_url": f"{forms}/linkedin_job.html"})
    run_extension(ctx, base, "dry run")
    acme = service.repo.get(1, jobs["Acme"]["id"])
    assert acme["status"] == "filled", acme["message"]
    assert service.applications.repo.for_user(1) == []  # a dry run applies to nothing
