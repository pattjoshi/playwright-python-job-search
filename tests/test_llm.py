import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from job_search.llm import JobMatcherLLM
from job_search.models import Job, Profile


def fake_client(*replies):
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))]) for reply in replies
    ]
    return client


def test_extract_profile():
    reply = json.dumps(
        {
            "current_title": "QA Automation Engineer",
            "target_titles": ["SDET", "Automation Engineer"],
            "skills": ["Python", "Playwright", " "],
            "years_experience": "4",
            "locations": ["Bengaluru"],
            "search_queries": ["Python Automation Engineer"],
            "summary": "QA engineer.",
        }
    )
    llm = JobMatcherLLM("key", "model", client=fake_client(reply))

    profile = llm.extract_profile("resume text")

    assert profile.current_title == "QA Automation Engineer"
    assert profile.skills == ["Python", "Playwright"]
    assert profile.years_experience == 4.0
    assert profile.search_queries == ["Python Automation Engineer"]


def test_score_jobs_batches_and_clamps():
    jobs = [Job("linkedin", str(i), f"Job {i}", "Co", "Pune", "u") for i in range(3)]
    replies = [
        json.dumps(
            {
                "results": [
                    {"id": "linkedin:0", "score": 140, "reason": "great", "matched_skills": ["Python"], "missing_skills": ["Go"]},
                    {"id": "linkedin:1", "score": 40},
                ]
            }
        ),
        json.dumps({"results": [{"id": "unknown", "score": 90}]}),
    ]
    client = fake_client(*replies)
    llm = JobMatcherLLM("key", "model", client=client)

    llm.score_jobs(Profile(skills=["Python"]), jobs, batch_size=2)

    assert client.chat.completions.create.call_count == 2
    assert (jobs[0].score, jobs[0].match_reason) == (100, "great")
    assert (jobs[0].matched_skills, jobs[0].missing_skills) == (["Python"], ["Go"])
    assert jobs[1].score == 40
    assert jobs[2].score is None


def test_invalid_json_is_ignored():
    llm = JobMatcherLLM("key", "model", client=fake_client("not json"))
    assert llm.extract_profile("resume").skills == []
