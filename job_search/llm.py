"""OpenAI calls: read the resume into a Profile, and score jobs against it."""

import json
import logging
from collections.abc import Callable

from openai import OpenAI

from job_search.models import Job, Profile

log = logging.getLogger(__name__)

PROFILE_PROMPT = """You are a career assistant. Read the resume and return a JSON object with:
- "current_title": the candidate's most recent job title
- "target_titles": 3-5 job titles they are a strong fit for right now
- "skills": up to 20 key technical and domain skills, most important first
- "years_experience": total professional experience in years (number, or null if unclear)
- "locations": cities/countries they live in or prefer, most likely first (empty list if unknown)
- "search_queries": 2-4 short job-board search phrases (like "Python Automation Engineer") that would find the best-matching jobs
- "summary": one sentence describing the candidate
Return only JSON."""

SCORING_PROMPT = """You are a recruiter screening jobs for one candidate.
For each job, give a match score from 0 to 100 based on how well the candidate's skills,
experience level and target roles fit the job, and a one-sentence reason. Be strict: 80+
only for strong fits. If the candidate gives a wanted experience range (years), score jobs
that clearly require experience outside that range low. Also list the candidate's skills that the job asks for
("matched_skills") and up to 5 important skills the job wants that the candidate lacks
("missing_skills"). Use short skill names like "Python" or "REST API testing".
Return JSON: {"results": [{"id": "<job id>", "score": <int>, "reason": "<text>",
"matched_skills": ["..."], "missing_skills": ["..."]}]}"""

MAX_DESCRIPTION_CHARS = 1500


class JobMatcherLLM:
    def __init__(self, api_key: str, model: str, client: OpenAI | None = None):
        self.model = model
        self.client = client or OpenAI(api_key=api_key)

    def extract_profile(self, resume_text: str) -> Profile:
        data = self._ask_json(PROFILE_PROMPT, resume_text)
        return Profile(
            current_title=str(data.get("current_title") or ""),
            target_titles=_str_list(data.get("target_titles")),
            skills=_str_list(data.get("skills")),
            years_experience=_float_or_none(data.get("years_experience")),
            locations=_str_list(data.get("locations")),
            search_queries=_str_list(data.get("search_queries")),
            summary=str(data.get("summary") or ""),
        )

    def score_jobs(
        self,
        profile: Profile,
        jobs: list[Job],
        batch_size: int = 10,
        experience: tuple[int, int] | None = None,
        before_batch: Callable[[int, int], None] | None = None,
    ) -> None:
        """Fill in score, reason and matched/missing skills on each job, in place.

        before_batch(done, total) runs before each request; it may raise to stop early.
        """
        candidate = {
            "summary": profile.summary,
            "current_title": profile.current_title,
            "target_titles": profile.target_titles,
            "skills": profile.skills,
            "years_experience": profile.years_experience,
        }
        if experience:
            candidate["wanted_experience_years"] = {"min": experience[0], "max": experience[1]}
        candidate = json.dumps(candidate)
        for start in range(0, len(jobs), batch_size):
            if before_batch:
                before_batch(start, len(jobs))
            batch = jobs[start : start + batch_size]
            by_id = {_job_ref(job): job for job in batch}
            payload = [
                {
                    "id": _job_ref(job),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "experience": job.experience,
                    "description": job.description[:MAX_DESCRIPTION_CHARS],
                }
                for job in batch
            ]
            log.info("Scoring jobs %d-%d of %d", start + 1, start + len(batch), len(jobs))
            data = self._ask_json(SCORING_PROMPT, f"CANDIDATE:\n{candidate}\n\nJOBS:\n{json.dumps(payload)}")
            for result in data.get("results") or []:
                job = by_id.get(str(result.get("id")))
                if job is None:
                    continue
                score = _float_or_none(result.get("score"))
                job.score = None if score is None else max(0, min(100, round(score)))
                job.match_reason = str(result.get("reason") or "")
                job.matched_skills = _str_list(result.get("matched_skills"))
                job.missing_skills = _str_list(result.get("missing_skills"))

    def _ask_json(self, system: str, user: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            log.warning("Model returned invalid JSON; ignoring this response")
            return {}
        return data if isinstance(data, dict) else {}


def _job_ref(job: Job) -> str:
    # Prefix with the source so IDs from different boards can't collide.
    return f"{job.source}:{job.job_id}"


def _str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
