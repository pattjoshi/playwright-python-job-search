"""Saved job descriptions, scores and resume readings (the cache that saves time and AI cost)."""

from job_search.models import Job, Profile
from job_search.repositories import CacheRepository, profile_key, resume_key


def job(job_id, source="linkedin", **kwargs):
    return Job(source, job_id, f"Job {job_id}", "Co", "Pune", f"https://example.com/{job_id}", **kwargs)


def test_cache_descriptions_scores_profiles(tmp_path):
    cache = CacheRepository(tmp_path / "cache.sqlite3")
    cache.save_descriptions([job("1", description="Python role", experience="2-4 Yrs"), job("2")])  # empty not saved

    jobs = [job("1"), job("2")]
    assert [j.job_id for j in cache.fill_descriptions(jobs)] == ["2"]
    assert (jobs[0].description, jobs[0].experience) == ("Python role", "2-4 Yrs")

    scored = job("1", score=88, match_reason="fit", matched_skills=["Python"], missing_skills=["Go"])
    cache.save_scores([scored, job("2")], "key-a")  # unscored job isn't cached
    fresh = [job("1"), job("2")]
    assert [j.job_id for j in cache.fill_scores(fresh, "key-a")] == ["2"]
    assert (fresh[0].score, fresh[0].match_reason, fresh[0].matched_skills, fresh[0].missing_skills) == (88, "fit", ["Python"], ["Go"])
    assert len(cache.fill_scores([job("1")], "key-b")) == 1  # other profile -> not reused

    cache.save_profile("r1", Profile(skills=["Python"], years_experience=3))
    assert cache.get_profile("r1") == Profile(skills=["Python"], years_experience=3)
    assert cache.get_profile("nope") is None


def test_cache_keys(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "renamed.txt"
    a.write_text("same resume")
    b.write_text("same resume")
    assert resume_key(a, "m") == resume_key(b, "m") != resume_key(a, "other-model")

    base = profile_key(Profile(skills=["Python"]), (1, 2), "m", "prompt")
    assert base == profile_key(Profile(skills=["Python"]), (1, 2), "m", "prompt")
    assert base != profile_key(Profile(skills=["Python", "Go"]), (1, 2), "m", "prompt")
    assert base != profile_key(Profile(skills=["Python"]), (1, 3), "m", "prompt")
    assert base != profile_key(Profile(skills=["Python"]), (1, 2), "m", "prompt v2")


def test_cache_delete_older_than(tmp_path):
    cache = CacheRepository(tmp_path / "c.sqlite3")
    cache.save_descriptions([job("old", description="x"), job("new", description="y")])
    with cache._db.connect() as db:
        db.execute("UPDATE job_details SET saved_at = '2000-01-01T00:00:00' WHERE job_id = 'old'")
    assert cache.delete_older_than(30) == 1
    assert [j.job_id for j in cache.fill_descriptions([job("old"), job("new")])] == ["old"]
