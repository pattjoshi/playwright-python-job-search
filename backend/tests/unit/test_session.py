from job_search.models import Profile
from job_search.repositories import SessionRepository

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
