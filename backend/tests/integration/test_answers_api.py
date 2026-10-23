"""Answer Bank through the web API (fake AI)."""

from pathlib import Path

from tests.answer_fakes import fake_ai

RESUME = Path(__file__).parents[1] / "sample_resume.txt"


def test_crud_and_counts(make_client):
    client, _ = make_client()
    assert client.post("/api/answers", json={"answer": "x"}).json() == {"error": "Question is required."}
    added = client.post("/api/answers", json={"question": "Notice period", "category": "availability",
                                              "wordings": ["How soon can you join?"]}).json()["answer"]
    assert added["status"] == "needs_answer" and added["wordings"] == ["How soon can you join?"]
    assert client.post("/api/answers", json={"question": "Notice Period?"}).status_code == 409

    edited = client.patch(f"/api/answers/{added['id']}", json={"answer": "30 days"}).json()["answer"]
    assert edited["status"] == "answered"
    listed = client.get("/api/answers?category=availability&q=notice").json()
    assert [a["id"] for a in listed["answers"]] == [added["id"]] and listed["counts"]["answered"] == 1
    assert client.get("/api/answers?status=maybe").status_code == 400

    assert client.delete(f"/api/answers/{added['id']}").json() == {"ok": True}
    assert client.delete(f"/api/answers/{added['id']}").status_code == 404


def test_starters_and_fill_from_resume(make_client):
    llm, ai = fake_ai(fill=lambda user: {"results": [{"id": 1, "found": True, "answer": "Om Prakash"}]})
    client, _ = make_client(answer_ai=lambda: ai)
    assert client.post("/api/answers/fill-from-resume").json() == {"error": "Upload your resume on the Search jobs page first."}

    with RESUME.open("rb") as file:
        assert client.post("/api/analyze", files={"resume": ("cv.txt", file, "text/plain")}).status_code == 200
    added = client.post("/api/answers/starters").json()["added"]
    assert added > 20 and client.get("/api/answers").json()["counts"]["needs_answer"] == added
    assert client.post("/api/answers/fill-from-resume").json() == {"filled": 1}
    assert "Python" in llm.calls[-1][1]  # the resume text went to the AI

    review = client.get("/api/answers?status=needs_review").json()["answers"]
    assert [(a["question"], a["answer"]) for a in review] == [("Full name", "Om Prakash")]
    approved = client.post(f"/api/answers/{review[0]['id']}/approve").json()["answer"]
    assert approved["status"] == "answered"


def test_try_a_question_adds_unknown_ones(make_client):
    client, _ = make_client()  # no AI: exact wordings only
    client.post("/api/answers", json={"question": "Notice period", "answer": "30 days", "wordings": ["How soon can you join?"]})
    assert client.post("/api/answers/try", json={"question": "How soon can you join? *"}).json()["answer"] == "30 days"

    unknown = client.post("/api/answers/try", json={"question": "Expected CTC?", "options": [], "asked_by": "Acme · SDET"}).json()
    assert unknown["how"] == "new" and unknown["answer"] is None
    assert unknown["entry"]["status"] == "needs_answer" and unknown["entry"]["asked_by"] == "Acme · SDET"
    assert client.get("/api/answers?status=needs_answer").json()["answers"][0]["question"] == "Expected CTC?"
    assert client.post("/api/answers/try", json={"question": ""}).json() == {"error": "Question is required."}


def test_answers_need_sign_in_and_belong_to_you(make_client):
    client, _ = make_client()
    client.post("/api/answers", json={"question": "Notice period"})
    client.post("/api/auth/logout")
    assert client.get("/api/answers").status_code == 401
