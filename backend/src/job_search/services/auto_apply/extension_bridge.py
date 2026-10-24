"""What the Chrome extension asks of the app: the next Easy Apply job, answers, and where to report results.

The extension applies in your own Chrome (already signed in to the boards). The rules stay here: only boards
you turned on, their daily limits, dry run, the Answer Bank (unknown required questions → "needs answer").
"""

import base64
import binascii
from datetime import datetime

from job_search.services.auto_apply.boards import BOARDS
from job_search.services.auto_apply.boards.linkedin import job_page_url
from job_search.services.auto_apply.rules import COMPANY_PLATFORMS, AutoApplyError, remaining_today
from job_search.services.auto_apply.service import AutoApplyService

RESULT_STATUSES = ("filled", "submitted", "unconfirmed", "needs_answer", "blocked", "failed")
MAX_SCREENSHOT = 8 * 1024 * 1024
MAX_PAGE = 4 * 1024 * 1024


class ExtensionBridge:
    def __init__(self, service: AutoApplyService):
        self.service = service

    def status(self, user_id: int) -> dict:
        settings = self.service.repo.settings(user_id)
        left = remaining_today(settings, self.service.repo.done_today(user_id, self.service.today().isoformat()))
        boards = {board: {"on": settings[board], "left_today": left[board]} for board in BOARDS}
        waiting = sum(1 for job in self.service.repo.for_user(user_id) if job["status"] == "queued" and job["platform"] in BOARDS)
        return {"dry_run": settings["dry_run"], "boards": boards, "waiting": waiting, "has_resume": self.service.resume_path() is not None}

    def claim_next(self, user_id: int) -> dict | None:
        """The best queued Easy Apply job on a board that is on and under its limit (marked "Applying…")."""
        settings = self.service.repo.settings(user_id)
        left = remaining_today(settings, self.service.repo.done_today(user_id, self.service.today().isoformat()))
        skip = (*COMPANY_PLATFORMS, *(board for board in BOARDS if not settings[board] or not left[board]))
        job = self.service.repo.next_queued(user_id, skip)
        if job is None:
            return None
        self.service.repo.update(user_id, job["id"], {"status": "running", "attempts": job["attempts"] + 1})
        url = job_page_url(job["apply_url"]) if job["platform"] == "linkedin" else job["apply_url"]
        return {"id": job["id"], "platform": job["platform"], "title": job["title"], "company": job["company"],
                "url": url, "dry_run": settings["dry_run"]}

    def answer(self, user_id: int, job_id: int, question: str, options: list, required: bool) -> dict:
        job = self._job(user_id, job_id)
        found = self.service.answers.resolve(user_id, question, [str(o) for o in options][:30], f"{job['company']} · {job['title']}",
                                             add_if_missing=bool(required))
        return {"answer": found["answer"], "how": found["how"]}

    def write(self, user_id: int, job_id: int, question: str) -> str:
        """A cover letter (question "Cover letter") or a short "why us?" answer for this job ("" without AI or resume)."""
        job = self._job(user_id, job_id)
        ai, resume_text = self.service.ai_factory(), self.service.resume_text()
        if not (ai and resume_text):
            return ""
        return ai.write_for_job(str(question)[:300], job["title"], job["company"], job.get("description", ""), resume_text)

    def report(self, user_id: int, job_id: int, body: dict) -> dict:
        """Save what happened (status, message, answers used, screenshot, page) and track submitted jobs."""
        job = self._job(user_id, job_id)
        status = body.get("status")
        if status not in RESULT_STATUSES:
            raise AutoApplyError(f"status must be one of {', '.join(RESULT_STATUSES)}")
        answers = [{"question": str(a.get("question", ""))[:500], "answer": str(a.get("answer", ""))[:500],
                    "how": str(a.get("how", ""))[:20]} for a in (body.get("answers") or [])[:200] if isinstance(a, dict)]
        shot = self._save_screenshot(job_id, body.get("screenshot"))
        page = str(body.get("page") or "")
        if page and status not in ("filled", "submitted"):
            (self.service.files_dir / f"{job_id}.html").write_text(page[:MAX_PAGE], encoding="utf-8")
        updated = self.service.repo.update(user_id, job_id, {
            "status": status, "message": str(body.get("message") or "")[:1000], "answers": answers, "screenshot": shot or job["screenshot"],
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        })
        if status in ("submitted", "unconfirmed"):
            self.service.applications.track_job(user_id, {**job, "job_id": job["source_job_id"], "url": job["job_url"]}, "applied")
        if body.get("signed_in") and job["platform"] in BOARDS:
            self.service.sign_ins.mark(job["platform"])
        return updated

    def _save_screenshot(self, job_id: int, data_url) -> str:
        if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
            return ""
        try:
            raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
        except (IndexError, binascii.Error):
            return ""
        if len(raw) > MAX_SCREENSHOT or not raw.startswith((b"\x89PNG", b"\xff\xd8")):
            return ""
        name = f"{job_id}.png"
        self.service.files_dir.mkdir(parents=True, exist_ok=True)
        (self.service.files_dir / name).write_bytes(raw)
        return name

    def _job(self, user_id: int, job_id: int) -> dict:
        job = self.service.repo.get(user_id, job_id)
        if job is None:
            raise AutoApplyError("That job isn't in your auto-apply list.", status=404)
        return job
