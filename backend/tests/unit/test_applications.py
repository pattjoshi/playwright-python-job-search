"""Application tracker rules and storage (no web server)."""

from datetime import date

import pytest

from job_search.repositories import ApplicationRepository, UserRepository
from job_search.services.applications import ApplicationError, ApplicationService, clean

TODAY = date(2026, 10, 23)


@pytest.fixture
def service(tmp_path):
    path = tmp_path / "h.sqlite3"
    users = UserRepository(path)
    users.create("om@example.com", "Om", "x", "owner")
    users.create("other@example.com", "Other", "x", "member")
    return ApplicationService(ApplicationRepository(path), today=lambda: TODAY)


def test_validation_messages():
    with pytest.raises(ApplicationError, match="Company is required"):
        clean({"title": "SDET"}, creating=True)
    with pytest.raises(ApplicationError, match="http"):
        clean({"company": "A", "title": "B", "url": "javascript:alert(1)"}, creating=True)
    with pytest.raises(ApplicationError, match="date like"):
        clean({"follow_up_on": "next week"}, creating=False)
    with pytest.raises(ApplicationError, match="Status must be one of"):
        clean({"status": "ghosted"}, creating=False)
    assert clean({"company": "  Infosys ", "title": "SDET", "source": "monster"}, creating=True) == {
        "company": "Infosys", "title": "SDET", "source": "other",
    }


def test_create_move_and_timeline(service):
    app = service.create(1, {"company": "Infosys", "title": "SDET"})
    assert app["status"] == "saved" and app["applied_on"] is None

    moved = service.update(1, app["id"], {"status": "interview", "notes": "Round 1 on Monday"})
    assert moved["status"] == "interview" and moved["applied_on"] == "2026-10-23"  # date filled in when it moves past Saved
    events = service.repo.events(1, app["id"])
    assert [(e["kind"], e["from_status"], e["to_status"]) for e in events] == [("status", "saved", "interview"), ("created", None, "saved")]

    service.update(1, app["id"], {"notes": "Round 1 on Monday"})  # nothing changed: no new event
    assert len(service.repo.events(1, app["id"])) == 2


def test_each_user_only_sees_their_own(service):
    mine = service.create(1, {"company": "Infosys", "title": "SDET"})
    assert service.repo.for_user(2) == []
    assert service.repo.get(2, mine["id"]) is None
    with pytest.raises(ApplicationError) as error:
        service.update(2, mine["id"], {"status": "offer"})
    assert error.value.status == 404
    assert service.repo.delete(2, mine["id"]) is False and service.repo.get(1, mine["id"])


def test_track_job_once_and_upgrade_saved_to_applied(service):
    job = {"source": "naukri", "job_id": "n1", "title": "SDET", "company": "TCS", "url": "https://x.test/n1", "location": "Pune"}
    first, created = service.track_job(1, job)
    again, created_again = service.track_job(1, job, "applied")
    assert created and not created_again and again["id"] == first["id"]
    assert again["status"] == "applied" and again["applied_on"] == "2026-10-23"


def test_search_and_stats(service):
    applied = {"status": "applied", "applied_on": "2026-10-22", "follow_up_on": "2026-10-30"}
    service.create(1, {"company": "Infosys", "title": "SDET", **applied})
    service.create(1, {"company": "TCS", "title": "Python Developer", "status": "offer", "follow_up_on": "2026-10-25"})
    service.create(1, {"company": "Wipro", "title": "QA", "notes": "referral from Ravi"})

    assert [a["company"] for a in service.repo.for_user(1, query="ravi")] == ["Wipro"]
    assert [a["company"] for a in service.repo.for_user(1, status="offer")] == ["TCS"]
    stats = service.repo.stats(1, TODAY)
    assert stats["total"] == 3 and stats["by_status"] == {"applied": 1, "offer": 1, "saved": 1}
    assert stats["per_day"][-2:] == [{"date": "2026-10-22", "count": 1}, {"date": "2026-10-23", "count": 1}]
    assert [a["company"] for a in stats["follow_ups"]] == ["Infosys"]  # offers don't need a follow-up
