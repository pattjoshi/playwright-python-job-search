"""Search speed and match quality: repeats skipped, recent searches reused, loose titles dropped, fresher first."""

from datetime import datetime, timedelta

from job_search.models import Job
from job_search.repositories import CacheRepository
from job_search.services.matching_service import dedupe, rank_key, title_fits
from job_search.services.scraping.base import BaseScraper
from job_search.services.search import sites
from job_search.services.search.sites import collect_site, search_key


def job(job_id, title="AI Engineer", company="Acme", location="Pune", **kwargs):
    return Job("linkedin", job_id, title, company, location, f"https://example.com/{job_id}", **kwargs)


class FakeBoard(BaseScraper):
    name = "linkedin"

    def __init__(self, results):
        super().__init__(context=None, delay_range=(0, 0))
        self.results, self.calls = results, []

    def search(self, query, location):
        self.calls.append((query, location))
        return [job(i, hours_ago=1) for i in self.results.get(query, [])]


def test_same_role_on_two_boards_is_one_job():
    linkedin = job("1", "Sr. AI Engineer (Remote)", "Acme Technologies Pvt Ltd", "Bengaluru, Karnataka, India")
    naukri = Job("naukri", "2", "Senior AI Engineer", "ACME", "Bengaluru", "u")
    other_city = Job("naukri", "3", "Senior AI Engineer", "ACME", "Pune", "u")
    assert dedupe([linkedin, naukri, other_city]) == [linkedin, other_city]


def test_title_fits_drops_loose_matches_only():
    queries, terms = ["AI Engineer", "LLM Engineer"], ["Python", "RAG", "GenAI Engineer"]
    assert title_fits(job("1", "Machine Learning Engineer"), queries, terms)
    assert title_fits(job("2", "Data Scientist", description="Build RAG pipelines in Python"), queries, terms)
    assert not title_fits(job("3", "Sales Executive"), queries, terms)
    assert not title_fits(job("4", "Senior Lead (Urgent Hiring)"), queries, terms)  # filler words don't count
    assert title_fits(job("5", "Anything"), [], [])  # nothing to compare with: keep everything


def test_equal_scores_newest_first():
    old, new, best = job("1", score=80, hours_ago=20), job("2", score=80, hours_ago=2), job("3", score=90, hours_ago=50)
    unknown = job("4", score=80)
    assert sorted([old, unknown, new, best], key=rank_key, reverse=True) == [best, new, old, unknown]


def test_page_of_repeats_stops_the_search():
    board = FakeBoard({})
    assert not board.nothing_new([job("1"), job("2")])
    assert board.nothing_new([job("2"), job("1")])  # "Gen AI Engineer" returned what "AI Engineer" did
    assert not board.nothing_new([job("1"), job("3")])  # one new job is worth the next page
    assert not board.nothing_new([])


def test_recent_searches_are_reused(tmp_path, monkeypatch):
    cache = CacheRepository(tmp_path / "cache.sqlite3")
    first = FakeBoard({"AI Engineer": ["1", "2"], "LLM Engineer": ["3"]})
    jobs = collect_site(first, "linkedin", ["AI Engineer", "LLM Engineer"], ["Pune"], cache=cache)
    assert len(first.calls) == 2 and len(jobs) == 3

    again = FakeBoard({"AI Engineer": ["9"]})
    jobs = collect_site(again, "linkedin", ["AI Engineer", "LLM Engineer"], ["Pune"], cache=cache)
    assert again.calls == [] and [j.job_id for j in jobs] == ["1", "2", "3"]
    assert jobs[0].hours_ago > 1 - 0.01 and again.found_ids == {"1", "2", "3"}

    # Another city, or a different time window, is a different search.
    collect_site(again, "linkedin", ["AI Engineer"], ["Delhi"], cache=cache)
    assert again.calls == [("AI Engineer", "Delhi")]


def test_old_or_refused_searches_are_searched_again(tmp_path):
    cache = CacheRepository(tmp_path / "cache.sqlite3")
    board = FakeBoard({"AI Engineer": ["1"]})
    key = search_key(board, "AI Engineer", "Pune")
    cache.save_search(key, [job("1", hours_ago=1)])
    with cache._db.lock, cache._db.connect() as db:
        db.execute("UPDATE searches SET saved_at = ?", ((datetime.now() - timedelta(hours=3)).isoformat(),))
    assert cache.get_search(key, sites.SEARCH_REUSE_HOURS) is None

    class Refused(FakeBoard):
        def search(self, query, location):
            self.blocked = True  # the site answered "Access Denied"
            return []

    refused = Refused({})
    collect_site(refused, "linkedin", ["AI Engineer"], ["Delhi"], cache=cache)
    assert cache.get_search(search_key(refused, "AI Engineer", "Delhi"), 2) is None
