"""Notes pages: blocks, pages inside pages, moving without loops, ownership (no web server)."""

import pytest

from job_search.repositories import NoteRepository, UserRepository
from job_search.services.notes import NoteError, NoteService, clean_blocks


@pytest.fixture
def service(tmp_path):
    path = tmp_path / "h.sqlite3"
    users = UserRepository(path)
    users.create("om@example.com", "Om", "x", "owner")
    users.create("other@example.com", "Other", "x", "member")
    return NoteService(NoteRepository(path))


def test_blocks_are_checked():
    assert clean_blocks([{"id": "a", "type": "todo", "text": "Call HR", "checked": 1}, {"type": "h1", "text": "X", "checked": True}]) == [
        {"id": "a", "type": "todo", "text": "Call HR", "checked": True}, {"id": "", "type": "h1", "text": "X", "checked": False},
    ]
    for bad in ("nope", [{"type": "table"}], [{"type": "paragraph", "text": "x" * 20_001}]):
        with pytest.raises(NoteError):
            clean_blocks(bad)


def test_pages_inside_pages_and_deleting_a_branch(service):
    prep = service.create(1, {"title": "Interview prep", "icon": "🎯"})
    infosys = service.create(1, {"title": "Infosys", "parent_id": prep["id"]})
    round1 = service.create(1, {"title": "Round 1", "parent_id": infosys["id"],
                                "content": [{"id": "b1", "type": "bullet", "text": "Tell me about yourself"}]})
    assert service.repo.get(1, round1["id"])["content"][0]["text"] == "Tell me about yourself"
    edited = service.update(1, round1["id"], {"title": "  Round 1 (tech) ", "content": [{"type": "todo", "text": "Revise SQL"}]})
    assert edited["title"] == "Round 1 (tech)" and edited["content"][0]["type"] == "todo"

    service.delete(1, prep["id"])  # the pages inside go with it
    assert service.repo.tree(1) == []


def test_move_reorders_and_refuses_loops(service):
    a, b, c = (service.create(1, {"title": t}) for t in "ABC")
    assert [p["title"] for p in service.move(1, c["id"], None, 0) if p["parent_id"] is None] == ["C", "A", "B"]
    tree = service.move(1, b["id"], a["id"], 0)
    assert next(p for p in tree if p["id"] == b["id"])["parent_id"] == a["id"]
    with pytest.raises(NoteError, match="inside itself"):
        service.move(1, a["id"], b["id"], 0)  # A can't go inside its own child B


def test_other_users_pages_are_invisible(service):
    page = service.create(1, {"title": "Private"})
    assert service.repo.tree(2) == [] and service.repo.get(2, page["id"]) is None
    for action in (lambda: service.update(2, page["id"], {"title": "x"}), lambda: service.delete(2, page["id"]),
                   lambda: service.create(2, {"title": "x", "parent_id": page["id"]})):
        with pytest.raises(NoteError) as error:
            action()
        assert error.value.status == 404
