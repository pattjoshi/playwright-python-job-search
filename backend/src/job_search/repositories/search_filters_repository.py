"""Search filters you set once and every search uses (web, daily, command line): kept in data/search-filters.json."""

import json
from pathlib import Path

DEFAULTS: dict = {"exclude_companies": []}
FILE = "search-filters.json"


class SearchFiltersRepository:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / FILE

    def load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        return {**DEFAULTS, **{k: v for k, v in (data if isinstance(data, dict) else {}).items() if k in DEFAULTS}}

    def save(self, filters: dict) -> dict:
        merged = {**self.load(), **{k: v for k, v in filters.items() if k in DEFAULTS}}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        return merged
