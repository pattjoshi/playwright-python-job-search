"""The AI's three jobs in the Answer Bank: spot reworded questions, draft answers from the resume, fill the starter set.

It never invents personal facts: anything the resume and saved answers don't state comes back as not found,
so the question waits in the bank for you to answer.
"""

import json

MATCH_PROMPT = """You match job application form questions to a candidate's saved questions.
Return the id of the saved question that asks for the SAME information (e.g. "How soon can you join?"
is the same as "Notice period"; "Expected CTC" is the same as "Salary expectations"). Questions that are
only related are NOT the same (current salary is not expected salary; total experience is not experience
with one skill). If no saved question asks for the same information, return null.
Return JSON: {"match_id": <id or null>}"""

DRAFT_PROMPT = """You help a candidate answer a job application form question.
Answer ONLY with facts stated in the RESUME or the SAVED ANSWERS. Never guess or invent personal facts:
salary, notice period, visa or work authorization, willingness to relocate or work shifts, dates, or
anything else not stated -> return found=false and an empty answer.
If OPTIONS are given, the answer must be exactly one of them. Keep answers short, the way a form expects
(a number for "years of", a URL for links, one or two sentences for open questions).
Also pick the category: personal, experience, compensation, availability, work_authorization or other.
Return JSON: {"found": <bool>, "answer": "<text>", "category": "<category>"}"""

FILL_PROMPT = """You fill in a candidate's saved application questions from their resume.
For each question, answer ONLY if the resume states it (name, email, phone, city, links, experience,
titles, companies, education, skills). Anything not stated (salary, notice period, visa, relocation,
preferences...) -> found=false and an empty answer. For yes/no questions answer "Yes" or "No" only when
the resume clearly says so. Keep answers short, the way a form expects.
Return JSON: {"results": [{"id": <id>, "found": <bool>, "answer": "<text>"}]}"""

WRITE_PROMPT = """You write for a candidate applying to one job. Use ONLY facts from the RESUME; never invent experience,
numbers, employers or skills. Make it specific to this job and company, in the first person, plain and warm,
with no placeholders like [Company] and no address block or sign-off name.
If the QUESTION is "Cover letter": 120-180 words in 2-3 short paragraphs. Otherwise answer the question in 2-4 sentences.
Return JSON: {"text": "<text>"}"""

MAX_RESUME_CHARS = 12000
MAX_JOB_CHARS = 5000

MATCH_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["match_id"],
    "properties": {"match_id": {"type": ["integer", "null"]}},
}
DRAFT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["found", "answer", "category"],
    "properties": {"found": {"type": "boolean"}, "answer": {"type": "string"}, "category": {"type": "string"}},
}
WRITE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["text"], "properties": {"text": {"type": "string"}},
}
FILL_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["results"],
    "properties": {"results": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "found", "answer"],
        "properties": {"id": {"type": "integer"}, "found": {"type": "boolean"}, "answer": {"type": "string"}},
    }}},
}


class AnswerAI:
    """Wraps a JobMatcherLLM (anything with `ask_json(system, user, name, schema)`)."""

    def __init__(self, llm):
        self.llm = llm

    def match(self, question: str, candidates: list[dict]) -> int | None:
        saved = [{"id": c["id"], "question": c["question"], "also_asked_as": c.get("wordings", [])[:5]} for c in candidates]
        user = f"FORM QUESTION: {question}\n\nSAVED QUESTIONS:\n{json.dumps(saved)}"
        match_id = self.llm.ask_json(MATCH_PROMPT, user, "question_match", MATCH_SCHEMA).get("match_id")
        ids = {c["id"] for c in candidates}
        return match_id if isinstance(match_id, int) and match_id in ids else None

    def draft(self, question: str, options: list[str], resume_text: str, facts: list[dict]) -> dict:
        """{"found", "answer", "category"}; found is False when the answer isn't stated anywhere."""
        user = (
            f"QUESTION: {question}\nOPTIONS: {json.dumps(options)}\n\n"
            f"SAVED ANSWERS:\n{json.dumps(facts)}\n\nRESUME:\n{resume_text[:MAX_RESUME_CHARS]}"
        )
        data = self.llm.ask_json(DRAFT_PROMPT, user, "answer_draft", DRAFT_SCHEMA)
        answer = str(data.get("answer") or "").strip()
        if options and answer not in options:
            answer = ""
        return {"found": bool(data.get("found")) and bool(answer), "answer": answer, "category": str(data.get("category") or "")}

    def fill(self, questions: list[dict], resume_text: str) -> dict[int, str]:
        """{id: answer} for the questions the resume answers."""
        asked = [{"id": q["id"], "question": q["question"], "kind": q["kind"]} for q in questions]
        user = f"QUESTIONS:\n{json.dumps(asked)}\n\nRESUME:\n{resume_text[:MAX_RESUME_CHARS]}"
        data = self.llm.ask_json(FILL_PROMPT, user, "answer_fill", FILL_SCHEMA)
        ids = {q["id"] for q in questions}
        return {
            item["id"]: str(item.get("answer") or "").strip()
            for item in data.get("results") or []
            if isinstance(item, dict) and item.get("id") in ids and item.get("found") and str(item.get("answer") or "").strip()
        }

    def write_for_job(self, question: str, title: str, company: str, description: str, resume_text: str) -> str:
        """A cover letter (question "Cover letter") or a short answer like "Why do you want to join us?"."""
        user = (
            f"QUESTION: {question}\n\nJOB: {title} at {company}\n{description[:MAX_JOB_CHARS]}\n\n"
            f"RESUME:\n{resume_text[:MAX_RESUME_CHARS]}"
        )
        return str(self.llm.ask_json(WRITE_PROMPT, user, "job_writing", WRITE_SCHEMA).get("text") or "").strip()
