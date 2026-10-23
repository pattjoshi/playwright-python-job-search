"""Notes rules: what a valid page and block look like, and moving pages without making loops."""

from job_search.repositories.note_repository import NoteRepository

BLOCK_TYPES = ("paragraph", "h1", "h2", "h3", "todo", "bullet", "numbered", "quote", "code", "divider")
MAX_BLOCKS = 2000
MAX_TEXT = 20_000
MAX_TITLE = 300


class NoteError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def clean_blocks(blocks) -> list[dict]:
    """Validated blocks: [{"id", "type", "text", "checked"}]. Raises NoteError."""
    if not isinstance(blocks, list) or len(blocks) > MAX_BLOCKS:
        raise NoteError(f"A page holds at most {MAX_BLOCKS} blocks.")
    cleaned = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") not in BLOCK_TYPES:
            raise NoteError(f"Each block needs a type: {', '.join(BLOCK_TYPES)}.")
        text = str(block.get("text") or "")
        if len(text) > MAX_TEXT:
            raise NoteError(f"A block can hold at most {MAX_TEXT} characters.")
        cleaned.append({"id": str(block.get("id") or "")[:40], "type": block["type"], "text": text,
                        "checked": bool(block.get("checked")) if block["type"] == "todo" else False})
    return cleaned


def _clean(fields: dict) -> dict:
    cleaned = {}
    if "title" in fields:
        cleaned["title"] = str(fields["title"] or "").strip()[:MAX_TITLE]
    if "icon" in fields:
        cleaned["icon"] = str(fields["icon"] or "").strip()[:8]
    if "content" in fields:
        cleaned["content"] = clean_blocks(fields["content"])
    return cleaned


class NoteService:
    def __init__(self, repo: NoteRepository):
        self.repo = repo

    def create(self, user_id: int, fields: dict) -> dict:
        cleaned = _clean(fields)
        parent_id = fields.get("parent_id")
        if parent_id is not None:
            self._get(user_id, parent_id)
        return self.repo.create(user_id, parent_id, cleaned.get("title", ""), cleaned.get("icon", ""), cleaned.get("content", []))

    def update(self, user_id: int, note_id: int, fields: dict) -> dict:
        self._get(user_id, note_id)
        return self.repo.update(user_id, note_id, _clean(fields))

    def move(self, user_id: int, note_id: int, parent_id: int | None, position: int) -> list[dict]:
        """Put the page under parent_id (None = top level) at position; returns the new tree."""
        self._get(user_id, note_id)
        pages = {page["id"]: page for page in self.repo.tree(user_id)}
        ancestor = parent_id
        while ancestor is not None:  # a page can't go inside itself or one of its own pages
            if ancestor == note_id:
                raise NoteError("A page can't be moved inside itself.")
            if ancestor not in pages:
                raise NoteError("That page doesn't exist.", status=404)
            ancestor = pages[ancestor]["parent_id"]
        siblings = [p["id"] for p in pages.values() if p["parent_id"] == parent_id and p["id"] != note_id]
        siblings.insert(max(0, min(position, len(siblings))), note_id)
        for index, sibling in enumerate(siblings):
            self.repo.update(user_id, sibling, {"parent_id": parent_id, "position": index} if sibling == note_id else {"position": index})
        return self.repo.tree(user_id)

    def delete(self, user_id: int, note_id: int) -> None:
        if not self.repo.delete(user_id, note_id):
            raise NoteError("That page doesn't exist.", status=404)

    def _get(self, user_id: int, note_id) -> dict:
        page = self.repo.get(user_id, note_id) if isinstance(note_id, int) else None
        if page is None:
            raise NoteError("That page doesn't exist.", status=404)
        return page
