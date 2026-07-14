"""Keyword source + publishing state.

Two files are used so the client can safely regenerate the keyword list from a
new ``.docx`` without losing publishing history:

* ``keywords.json``        — the master source: {category: [keyword, ...]}
* ``keywords.state.json``  — what has already been published (auto-managed)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Selection:
    category: str
    keyword: str


class KeywordTracker:
    def __init__(self, keywords_file: Path, state_file: Path):
        self.keywords_file = keywords_file
        self.state_file = state_file
        self.keywords: dict[str, list[str]] = {}
        self.state: dict[str, dict] = {"used": {}}
        self._load()

    def _load(self) -> None:
        if not self.keywords_file.exists():
            raise FileNotFoundError(
                f"Keyword file not found: {self.keywords_file}. "
                "Run 'python convert_docx.py <file.docx>' first."
            )
        raw = json.loads(self.keywords_file.read_text(encoding="utf-8"))
        self.keywords = _normalise_keywords(raw)

        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.state.setdefault("used", {})

    def _save_state(self) -> None:
        self.state_file.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- queries ------------------------------------------------------------
    def categories(self) -> list[str]:
        return list(self.keywords.keys())

    def is_used(self, category: str, keyword: str) -> bool:
        return keyword in self.state["used"].get(category, {})

    def next_unused(self, category: str) -> str | None:
        for keyword in self.keywords.get(category, []):
            if not self.is_used(category, keyword):
                return keyword
        return None

    def remaining(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for category, words in self.keywords.items():
            used = self.state["used"].get(category, {})
            out[category] = sum(1 for w in words if w not in used)
        return out

    def total_remaining(self) -> int:
        return sum(self.remaining().values())

    # -- mutations ----------------------------------------------------------
    def mark_used(
        self, category: str, keyword: str, *, post_id: int, url: str = ""
    ) -> None:
        self.state["used"].setdefault(category, {})[keyword] = {
            "published_at": datetime.now(timezone.utc).isoformat(),
            "post_id": post_id,
            "url": url,
        }
        self._save_state()


def _normalise_keywords(raw: dict) -> dict[str, list[str]]:
    """Accept both the plain format and the {'keyword','used'} object format."""
    result: dict[str, list[str]] = {}
    for category, items in raw.items():
        words: list[str] = []
        for item in items:
            if isinstance(item, str):
                words.append(item.strip())
            elif isinstance(item, dict) and "keyword" in item:
                words.append(str(item["keyword"]).strip())
        # de-duplicate while preserving order
        seen: set[str] = set()
        deduped = []
        for w in words:
            if w and w.lower() not in seen:
                seen.add(w.lower())
                deduped.append(w)
        result[category] = deduped
    return result
