"""OpenAI calls: read the resume into a Profile, and score jobs against it."""

import json
import logging
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from dataclasses import dataclass

from openai import BadRequestError, OpenAI

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
# Scoring requests in flight at once. OpenAI's client retries 429/5xx itself with backoff.
SCORING_CONCURRENCY = 4
MAX_RETRIES = 4


@dataclass
class TokenUsage:
    """What the AI calls of one run used (for the cost shown in the UI)."""

    calls: int = 0
    input_tokens: int = 0  # includes cached_tokens
    cached_tokens: int = 0  # input tokens OpenAI served from its prompt cache (cheaper)
    output_tokens: int = 0

    def cost_usd(self, input_price: float | None, output_price: float | None, cached_price: float | None = None) -> float | None:
        """Estimated cost with prices in USD per 1M tokens; None when prices aren't configured."""
        if input_price is None or output_price is None:
            return None
        cached_price = input_price if cached_price is None else cached_price
        uncached = self.input_tokens - self.cached_tokens
        return (uncached * input_price + self.cached_tokens * cached_price + self.output_tokens * output_price) / 1_000_000


def _strings() -> dict:
    return {"type": "array", "items": {"type": "string"}}


# Strict JSON schemas: the API guarantees replies in exactly this shape (no broken JSON).
PROFILE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["current_title", "target_titles", "skills", "years_experience", "locations", "search_queries", "summary"],
    "properties": {
        "current_title": {"type": "string"},
        "target_titles": _strings(),
        "skills": _strings(),
        "years_experience": {"type": ["number", "null"]},
        "locations": _strings(),
        "search_queries": _strings(),
        "summary": {"type": "string"},
    },
}
SCORES_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["results"],
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "score", "reason", "matched_skills", "missing_skills"],
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "integer"},
                    "reason": {"type": "string"},
                    "matched_skills": _strings(),
                    "missing_skills": _strings(),
                },
            },
        }
    },
}


class JobMatcherLLM:
    def __init__(self, api_key: str, model: str, client: OpenAI | None = None, concurrency: int = SCORING_CONCURRENCY):
        self.model = model
        self.client = client or OpenAI(api_key=api_key, max_retries=MAX_RETRIES, timeout=90)
        self.concurrency = max(1, concurrency)
        self._structured = True  # switched off if the model doesn't support strict schemas
        self.usage = TokenUsage()
        self._usage_lock = threading.Lock()  # scoring batches finish on several threads

    def extract_profile(self, resume_text: str) -> Profile:
        data = self._ask_json(PROFILE_PROMPT, resume_text, "resume_profile", PROFILE_SCHEMA)
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
        progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """Fill in score, reason and matched/missing skills on each job, in place.

        Batches are sent several at a time. progress(done, total) is called as batches finish
        (and once at the start); it may raise to stop early, which cancels batches not yet sent.
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
        candidate_json = json.dumps(candidate)
        by_id = {_job_ref(job): job for job in jobs}
        batches = [jobs[start : start + batch_size] for start in range(0, len(jobs), batch_size)]
        if progress:
            progress(0, len(jobs))
        if not batches:
            return

        def score_batch(batch: list[Job]) -> dict:
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
            user = f"CANDIDATE:\n{candidate_json}\n\nJOBS:\n{json.dumps(payload)}"
            return self._ask_json(SCORING_PROMPT, user, "job_scores", SCORES_SCHEMA)

        log.info("Scoring %d jobs in %d batches (%d at a time)", len(jobs), len(batches), self.concurrency)
        done = 0
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            pending = {pool.submit(score_batch, batch): len(batch) for batch in batches}
            try:
                while pending:
                    finished, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in finished:
                        done += pending.pop(future)
                        self._apply_scores(future.result(), by_id)
                    if progress:
                        progress(done, len(jobs))
            except BaseException:
                for future in pending:
                    future.cancel()
                raise

    @staticmethod
    def _apply_scores(data: dict, by_id: dict[str, Job]) -> None:
        for result in data.get("results") or []:
            job = by_id.get(str(result.get("id")))
            if job is None:
                continue
            score = _float_or_none(result.get("score"))
            job.score = None if score is None else max(0, min(100, round(score)))
            job.match_reason = str(result.get("reason") or "")
            job.matched_skills = _str_list(result.get("matched_skills"))
            job.missing_skills = _str_list(result.get("missing_skills"))

    def _ask_json(self, system: str, user: str, schema_name: str, schema: dict) -> dict:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        response = None
        if self._structured:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
                )
            except BadRequestError as error:
                if "response_format" not in str(error) and "json_schema" not in str(error):
                    raise
                log.info("%s doesn't support strict JSON schemas; using JSON mode instead", self.model)
                self._structured = False
        if response is None:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, response_format={"type": "json_object"}
            )
        self._count_usage(response)
        content = response.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            log.warning("Model returned invalid JSON; ignoring this response")
            return {}
        return data if isinstance(data, dict) else {}


    def _count_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        details = getattr(usage, "prompt_tokens_details", None)
        prompt, completion, cached = (
            getattr(usage, "prompt_tokens", 0),
            getattr(usage, "completion_tokens", 0),
            getattr(details, "cached_tokens", 0),
        )
        with self._usage_lock:
            self.usage.calls += 1
            self.usage.input_tokens += prompt if isinstance(prompt, int) else 0
            self.usage.output_tokens += completion if isinstance(completion, int) else 0
            self.usage.cached_tokens += cached if isinstance(cached, int) else 0


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
