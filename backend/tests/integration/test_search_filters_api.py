"""Saved search filters through the web API (the search step itself is tested in unit/test_search_filters.py)."""

from tests.integration.web_support import start, wait_done


def test_hide_a_company_then_search(make_client):
    client, _ = make_client()
    assert client.get("/api/search-filters").json() == {"filters": {"exclude_companies": []}}
    wait_done(client, start(client).json()["id"])
    first = client.get("/api/session").json()["last_job"]["result"]["sites"][0]["jobs"][0]
    assert "description" in first and "hours_ago" in first  # for the details panel and the filters

    hidden = client.post("/api/search-filters/hide-company", json={"company": first["company"]}).json()["filters"]
    assert hidden["exclude_companies"] == [first["company"]]
    assert client.post("/api/search-filters/hide-company", json={"company": ""}).status_code == 400
    assert client.put("/api/search-filters", json={"exclude_companies": ["A", "B"]}).json()["filters"]["exclude_companies"] == ["A", "B"]
    assert client.post("/api/search-filters/show-company", json={"company": "a"}).json()["filters"]["exclude_companies"] == ["B"]
    client.post("/api/auth/logout")
    assert client.get("/api/search-filters").status_code == 401
