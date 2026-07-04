"""Memory tools — agent cross-session facts remember/recall kar sake (Feature 10)."""
from __future__ import annotations

from ..core.memory import MEMORY
from .base import Tool


class Remember(Tool):
    name = "remember"
    description = (
        "Ek fact/preference/decision permanently yaad rakho (sessions ke across). "
        "key = short label, value = content, category = fact|preference|decision."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short unique label."},
                "value": {"type": "string", "description": "Content to remember."},
                "category": {"type": "string", "description": "fact|preference|decision (optional)."},
            },
            "required": ["key", "value"],
        }

    def run(self, workdir: str, key: str, value: str, category: str = "fact", **_) -> str:
        return MEMORY.remember(key, value, category)


class Recall(Tool):
    name = "recall"
    description = "Yaad kiye hue facts search karo. query = keyword (khaali = sab)."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword (optional)."},
            },
        }

    def run(self, workdir: str, query: str = "", **_) -> str:
        return MEMORY.recall(query)
