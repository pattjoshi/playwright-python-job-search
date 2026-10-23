"""A stand-in for the OpenAI client in Answer Bank tests: replies by request type, records what was asked."""

from job_search.services.answers import AnswerAI


class FakeAnswerLLM:
    def __init__(self, match=None, draft=None, fill=None, writing=None):
        self.replies = {"job_writing": writing or (lambda user: {"text": f"Letter: {user.splitlines()[0]}"}),
                        "question_match": match or {"match_id": None},
                        "answer_draft": draft or {"found": False, "answer": "", "category": "other"},
                        "answer_fill": fill or {"results": []}}
        self.calls: list[tuple[str, str]] = []

    def ask_json(self, system, user, schema_name, schema):
        self.calls.append((schema_name, user))
        reply = self.replies[schema_name]
        return reply(user) if callable(reply) else reply

    def asked(self, schema_name: str) -> int:
        return sum(1 for name, _ in self.calls if name == schema_name)


def fake_ai(**replies) -> tuple[FakeAnswerLLM, AnswerAI]:
    llm = FakeAnswerLLM(**replies)
    return llm, AnswerAI(llm)
