"""Shared API error type and the small validation helpers routes use on raw request bodies.

Request bodies are kept as plain dicts (not strict Pydantic models) for the search/schedule
endpoints: the original hand-written messages ("Experience 'from' can't be more than 'to'.")
are part of the app's behavior, and FastAPI's own 422 schema-validation errors would replace
them with a generic shape FastAPI's frontend doesn't expect. Pydantic models are still used
for shapes that don't need custom per-field messages (see the other schemas/*.py files).
"""


class ApiError(Exception):
    """Raised by a route to send `{"error": message}` back to the frontend."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def int_in_range(value, label: str, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{label} must be a whole number.") from None
    if not low <= number <= high:
        raise ApiError(f"{label} must be between {low} and {high}.")
    return number


def str_list(value, label: str, max_items: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ApiError(f"{label} must be a list.")
    items = []
    for item in value:
        text = " ".join(str(item).split())[:80]
        if text and text not in items:
            items.append(text)
    if len(items) > max_items:
        raise ApiError(f"Use at most {max_items} {label}.")
    return items
