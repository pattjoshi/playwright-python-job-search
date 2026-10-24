"""Saved search filters: hidden companies, matched ignoring case, punctuation and "Pvt Ltd"."""

import pytest

from job_search.models import Job, SearchOptions
from job_search.repositories.search_filters_repository import SearchFiltersRepository
from job_search.services.search.filters import apply_filters
from job_search.services.search_filters import FilterError, SearchFilterService, company_key, without_companies


def job(company, job_id="1"):
    return Job("naukri", job_id, "SDET", company, "Pune", "https://x.test/" + job_id, hours_ago=1)


def test_company_names_match_loosely():
    assert company_key("Acme Technologies Pvt. Ltd.") == company_key("ACME") == "acme"
    assert company_key("Tata Consultancy Services Limited") == "tata consultancy services"
    jobs = [job("Acme Pvt Ltd", "1"), job("Beta", "2"), job("acme", "3")]
    assert [j.job_id for j in without_companies(jobs, ["ACME"])] == ["2"]
    assert without_companies(jobs, []) == jobs


def test_hide_and_show_companies(tmp_path):
    service = SearchFilterService(SearchFiltersRepository(tmp_path))
    assert service.get() == {"exclude_companies": []}
    service.hide_company("Acme Pvt Ltd")
    assert service.hide_company("ACME")["exclude_companies"] == ["Acme Pvt Ltd"]  # the same company once
    assert service.show_company("acme")["exclude_companies"] == []
    with pytest.raises(FilterError):
        service.hide_company("  ")
    with pytest.raises(FilterError):
        service.save({"exclude_companies": "Acme"})
    assert SearchFiltersRepository(tmp_path).load() == {"exclude_companies": []}  # kept in the file


def test_the_funnel_counts_hidden_companies():
    steps = []
    kept, funnel = apply_filters([job("Acme", "1"), job("Beta", "2")], SearchOptions(resume_path="cv.pdf"), None,
                                 lambda *_a, **k: steps.append(k), exclude_companies=["acme"])
    assert [j.company for j in kept] == ["Beta"] and ("not from hidden companies", 1) in funnel
