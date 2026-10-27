import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from job_search.services.scraping.base import BaseScraper

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def browser():
    # Lets tests run where Playwright's bundled browser isn't installed but another Chromium is.
    executable = os.getenv("CHROMIUM_EXECUTABLE") or None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def fixture_html():
    return lambda name: (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def no_retry_waits(monkeypatch):
    """Retries still happen in tests, just without the real 8s/20s waits."""
    monkeypatch.setattr(BaseScraper, "retry_delays", (0.0, 0.0))


@pytest.fixture(autouse=True)
def fresh_postgres(monkeypatch):
    """With TEST_DATABASE_URL set (e.g. CI's Postgres), every test gets an empty Postgres database instead of SQLite."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        yield
        return
    from sqlalchemy import create_engine, text

    from job_search.database import engine as engines

    admin = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1))
    with admin.begin() as db:
        db.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    admin.dispose()
    monkeypatch.setenv("DATABASE_URL", url)
    engines._engines.clear()
    yield
    engines._engines.clear()
