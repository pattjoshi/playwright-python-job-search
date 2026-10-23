import time

from job_search.config import Settings
from job_search.models import Profile, SearchOptions
from job_search.repositories import SessionRepository
from job_search.services.matching_service import SearchStopped
from job_search.services.search_manager import SearchManager

PROFILE = Profile(current_title="GenAI Engineer", skills=["Python"], years_experience=3,
                  locations=["Bangalore"], search_queries=["GenAI Engineer"], summary="GenAI engineer")


def test_session_store(tmp_path):
    store = SessionRepository(tmp_path)
    assert store.load() == {} and store.resume() is None

    resume = tmp_path / "cv.pdf"
    resume.write_text("x")
    store.save_resume("r1", resume, "cv.pdf", PROFILE, [2, 4])
    store.save_last_job({"id": "j1", "status": "done"})
    assert store.resume()["profile"] == PROFILE
    assert store.load()["last_job"]["id"] == "j1"

    resume.unlink()  # deleted resume file: not offered any more
    assert store.resume() is None

    store.clear()
    assert store.load() == {}
    store.path.write_text("{ not json")
    assert store.load() == {}


def test_session_is_saved_before_the_search_shows_as_finished(tmp_path):
    """A "Clear" right after a search ends must not be undone by the search saving itself late."""
    saved = []

    class RecordingSession:
        def save_last_job(self, data):
            saved.append((data["status"], manager.jobs[data["id"]].status))

    def stopped_run(*_args, **_kwargs):
        raise SearchStopped()

    manager = SearchManager(Settings("key", history_path=tmp_path / "h.sqlite3"), tmp_path, stopped_run, RecordingSession())
    job = manager.start(SearchOptions(tmp_path / "cv.txt"), ["linkedin"])
    for _ in range(200):
        if not job.active:
            break
        time.sleep(0.01)

    assert job.status == "stopped"
    assert saved == [("stopped", "running")]  # saved while the page still saw it running
