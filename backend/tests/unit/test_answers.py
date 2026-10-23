"""Answer Bank rules, storage and how form questions get answered (fake AI, no web server)."""

import pytest

from job_search.repositories import AnswerRepository, UserRepository
from job_search.services.answers import AnswerError, AnswerService
from job_search.services.answers.matching import guess_kind, normalize, shortlist
from job_search.services.answers.service import clean
from job_search.services.answers.starters import STARTER_QUESTIONS
from tests.answer_fakes import fake_ai

RESUME = "Om Prakash · om@example.com · Pune · 3 years Python, FastAPI, RAG"


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "h.sqlite3"
    users = UserRepository(path)
    users.create("om@example.com", "Om", "x", "owner")
    users.create("other@example.com", "Other", "x", "member")
    return AnswerRepository(path)


def make(repo, ai=None, resume=RESUME):
    return AnswerService(repo, lambda: ai, lambda: resume)


def test_text_helpers():
    assert normalize("  Notice Period (in days)? * ") == "notice period in days"
    assert guess_kind([]) == "text" and guess_kind(["Yes", "No"]) == "yes_no" and guess_kind(["Remote", "Office"]) == "choice"
    bank = [{"id": i, "question": q, "wordings": []} for i, q in enumerate(["Notice period", "Expected CTC", "Full name"])]
    assert shortlist("What is your expected CTC?", bank, 1) == [bank[1]]
    assert shortlist("anything", bank, 5) == bank


def test_validation_messages():
    with pytest.raises(AnswerError, match="Question is required"):
        clean({"question": " ?? "}, creating=True)
    with pytest.raises(AnswerError, match="Category must be one of"):
        clean({"category": "hobbies"}, creating=False)
    with pytest.raises(AnswerError, match="Type must be one of"):
        clean({"kind": "essay"}, creating=False)
    assert clean({"question": " Notice period ", "wordings": ["How soon can you join?", "", "How soon can you join?"]}, True) == (
        {"question": "Notice period"}, ["How soon can you join?"],
    )


def test_crud_wordings_and_ownership(repo):
    service = make(repo)
    added = service.create(1, {"question": "Notice period", "category": "availability", "wordings": ["How soon can you join?"]})
    assert added["status"] == "needs_answer" and added["wordings"] == ["How soon can you join?"]
    with pytest.raises(AnswerError, match="already in your Answer Bank") as error:
        service.create(1, {"question": "notice period?"})
    assert error.value.status == 409

    answered = service.update(1, added["id"], {"answer": "30 days"})
    assert answered["status"] == "answered"
    renamed = service.update(1, added["id"], {"question": "Notice period (days)"})
    assert set(renamed["wordings"]) == {"Notice period", "How soon can you join?"}  # the old question is kept
    assert service.update(1, added["id"], {"answer": ""})["status"] == "needs_answer"

    assert repo.for_user(2) == [] and repo.get(2, added["id"]) is None  # another user can't see it
    with pytest.raises(AnswerError) as missing:
        service.update(2, added["id"], {"answer": "x"})
    assert missing.value.status == 404
    assert repo.delete(1, added["id"]) and repo.counts(1) == {"answered": 0, "needs_review": 0, "needs_answer": 0}


def test_starters_are_added_once(repo):
    service = make(repo)
    assert service.add_starters(1) == len(STARTER_QUESTIONS)
    assert service.add_starters(1) == 0
    notice = repo.find_by_key(1, normalize("How soon can you join?"))
    assert notice["question"] == "Notice period" and notice["source"] == "starter"


def test_fill_from_resume_waits_for_review(repo):
    service = make(repo)
    service.add_starters(1)
    ids = {a["question"]: a["id"] for a in repo.for_user(1)}
    llm, ai = fake_ai(fill={"results": [
        {"id": ids["Full name"], "found": True, "answer": "Om Prakash"},
        {"id": ids["Expected CTC (per year)"], "found": False, "answer": ""},
        {"id": ids["Are you willing to relocate?"], "found": True, "answer": "maybe"},  # not Yes/No: dropped
    ]})
    assert make(repo, ai).fill_from_resume(1) == 1
    name = repo.get(1, ids["Full name"])
    assert (name["answer"], name["status"], name["source"]) == ("Om Prakash", "needs_review", "resume")
    assert make(repo, ai).approve(1, name["id"])["status"] == "answered"
    with pytest.raises(AnswerError, match="Write an answer first"):
        service.approve(1, ids["Expected CTC (per year)"])
    with pytest.raises(AnswerError, match="OPENAI_API_KEY"):
        service.fill_from_resume(1)
    with pytest.raises(AnswerError, match="Upload your resume"):
        make(repo, ai, resume=None).fill_from_resume(1)


def test_resolve_saved_matched_drafted_new(repo):
    service = make(repo)
    notice = service.create(1, {"question": "Notice period", "answer": "30 days", "wordings": ["How soon can you join?"]})

    # 1. A wording you have: no AI needed.
    assert service.resolve(1, "How soon can you JOIN?")["answer"] == "30 days"

    # 2. A rewording the AI recognises: answered, and the wording is remembered (not sent to the AI again).
    llm, ai = fake_ai(match={"match_id": notice["id"]})
    result = make(repo, ai).resolve(1, "When can you start working with us?")
    assert (result["how"], result["answer"]) == ("matched", "30 days")
    assert make(repo, ai).resolve(1, "When can you start working with us")["how"] == "saved" and llm.asked("question_match") == 1
    assert repo.get(1, notice["id"])["use_count"] == 3

    # 3. Answerable from the resume: a draft, used now and waiting for review.
    llm, ai = fake_ai(draft={"found": True, "answer": "3", "category": "experience"})
    drafted = make(repo, ai).resolve(1, "Years of experience with Python", asked_by="Acme · SDET")
    assert (drafted["how"], drafted["answer"]) == ("drafted", "3")
    assert drafted["entry"]["status"] == "needs_review" and drafted["entry"]["asked_by"] == "Acme · SDET"
    assert '"30 days"' in llm.calls[-1][1]  # saved answers are given to the AI as facts

    # 4. Not in the resume or the bank: added for you to answer, and the form gets nothing.
    llm, ai = fake_ai(draft={"found": False, "answer": "", "category": "work_authorization"})
    new = make(repo, ai).resolve(1, "Do you hold a US work visa?", options=["Yes", "No"])
    assert (new["how"], new["answer"]) == ("new", None)
    entry = new["entry"]
    assert (entry["status"], entry["kind"], entry["options"]) == ("needs_answer", "yes_no", ["Yes", "No"])
    assert entry["category"] == "work_authorization"
    assert make(repo, ai).resolve(1, "Do you hold a US work visa?")["how"] == "saved"  # never added twice

    service.update(1, entry["id"], {"answer": "No"})  # you answer it once...
    assert make(repo, ai).resolve(1, "do you hold a us work visa")["answer"] == "No"  # ...and it's reused


def test_optional_questions_you_have_not_answered_are_not_added(repo):
    result = make(repo).resolve(1, "Twitter handle", add_if_missing=False)
    assert result == {"how": "skipped", "answer": None, "entry": None} and repo.for_user(1) == []


def test_resolve_without_ai_or_resume_adds_the_question(repo):
    result = make(repo, ai=None).resolve(1, "Expected CTC?")
    assert result["how"] == "new" and result["entry"]["source"] == "form"
    llm, ai = fake_ai(draft={"found": True, "answer": "Pune", "category": "personal"})
    assert make(repo, ai, resume=None).resolve(1, "Current city")["how"] == "new" and llm.asked("answer_draft") == 0


def test_ai_replies_are_checked(repo):
    """A match id that isn't one of yours, or a draft that isn't one of the options, is ignored."""
    service = make(repo)
    service.create(1, {"question": "Notice period", "answer": "30 days"})
    llm, ai = fake_ai(match={"match_id": 999}, draft={"found": True, "answer": "Maybe", "category": "nonsense"})
    result = make(repo, ai).resolve(1, "Are you open to relocation?", options=["Yes", "No"])
    assert result["how"] == "new" and result["entry"]["category"] == "other"


def test_app_wiring_needs_a_key_and_reads_the_saved_resume(tmp_path):
    from job_search.api.app import default_answer_ai, saved_resume_text
    from job_search.config import Settings
    from job_search.models import Profile
    from job_search.repositories import SessionRepository

    assert default_answer_ai(Settings(openai_api_key=""))() is None
    assert default_answer_ai(Settings(openai_api_key="sk-test"))() is not None
    session = SessionRepository(tmp_path)
    assert saved_resume_text(session)() is None
    resume = tmp_path / "cv.txt"
    resume.write_text(RESUME, encoding="utf-8")
    session.save_resume("r1", resume, "cv.txt", Profile(), None)
    assert saved_resume_text(session)() == RESUME
