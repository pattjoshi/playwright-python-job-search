"""Token/cost tracking and run history (pure, no browser)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import job_search.config.settings as settings_module
from job_search.config import load_settings
from job_search.models import Job, Profile, TokenUsage
from job_search.repositories import MAX_RUNS, JobHistoryRepository
from job_search.services.llm_service import JobMatcherLLM


def test_run_history_keeps_newest_runs(tmp_path):
    history = JobHistoryRepository(tmp_path / "h.sqlite3")
    for i in range(MAX_RUNS + 5):
        history.record_run(f"2026-10-01T00:00:{i:02d}", "cli", "done", {"n": i})
    runs = history.list_runs(limit=MAX_RUNS + 10)
    assert len(runs) == MAX_RUNS
    assert runs[0]["n"] == MAX_RUNS + 4


def test_token_usage_and_cost():
    def reply(prompt, completion, cached):
        usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=cached))
        return SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"results": []})))])

    client = MagicMock()
    client.chat.completions.create.side_effect = [reply(1200, 300, 1024), reply(800, 200, 0)]
    llm = JobMatcherLLM("key", "model", client=client, concurrency=2)
    llm.score_jobs(Profile(), [Job("linkedin", str(i), "t", "c", "l", "u") for i in range(15)])

    assert llm.usage == TokenUsage(calls=2, input_tokens=2000, cached_tokens=1024, output_tokens=500)
    assert llm.usage.cost_usd(None, 4.0) is None
    assert llm.usage.cost_usd(1.0, 4.0) == pytest.approx((2000 * 1 + 500 * 4) / 1_000_000)


def test_new_settings(monkeypatch):
    monkeypatch.setattr(settings_module, "load_dotenv", lambda *a, **k: None)
    for name in ("PARALLEL_SITES", "OPENAI_PRICE_INPUT", "OPENAI_PRICE_OUTPUT", "OPENAI_PRICE_CACHED_INPUT"):
        monkeypatch.delenv(name, raising=False)
    defaults = load_settings()
    assert defaults.parallel_sites is True and defaults.price_input is None

    monkeypatch.setenv("PARALLEL_SITES", "false")
    monkeypatch.setenv("OPENAI_PRICE_INPUT", "0.25")
    monkeypatch.setenv("OPENAI_PRICE_OUTPUT", "2")
    loaded = load_settings()
    assert (loaded.parallel_sites, loaded.price_input, loaded.price_output) == (False, 0.25, 2.0)

    monkeypatch.setenv("OPENAI_PRICE_INPUT", "cheap")
    with pytest.raises(ValueError, match="OPENAI_PRICE_INPUT"):
        load_settings()
