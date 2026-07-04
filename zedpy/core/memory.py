"""Cross-session memory — semantic search with categories and relationships.

Enhanced features:
  - Categories: fact, preference, decision, pattern, project
  - Semantic search: TF-IDF-like relevance ranking
  - Auto-pruning: remove stale entries after threshold
  - Session context: inject relevant memories into system prompt
  - Timestamped: track when entries were last accessed
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter
from pathlib import Path


def _mem_path() -> Path:
    d = Path(os.path.expanduser("~/.zedpy"))
    d.mkdir(parents=True, exist_ok=True)
    return d / "memory.json"


_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class Memory:
    def __init__(self, max_entries: int = 500):
        self.entries: list[dict] = []
        self.max_entries = max_entries
        self._load()

    def _load(self) -> None:
        p = _mem_path()
        if p.exists():
            try:
                self.entries = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                self.entries = []

    def _save(self) -> None:
        # Auto-prune if too many entries (keep most recently accessed)
        if len(self.entries) > self.max_entries:
            self.entries.sort(key=lambda e: e.get("accessed", e.get("updated", 0)),
                              reverse=True)
            self.entries = self.entries[:self.max_entries]
        _mem_path().write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def remember(self, key: str, value: str, category: str = "fact") -> str:
        """Store a fact/preference/decision with category and timestamp."""
        valid_cats = {"fact", "preference", "decision", "pattern", "project"}
        if category not in valid_cats:
            category = "fact"

        now = time.time()
        # Update existing entry if key matches
        for e in self.entries:
            if e["key"] == key:
                e.update(
                    value=value,
                    category=category,
                    updated=now,
                    access_count=e.get("access_count", 0) + 1,
                )
                self._save()
                return f"Updated memory: {key}"

        self.entries.append({
            "key": key,
            "value": value,
            "category": category,
            "created": now,
            "updated": now,
            "accessed": now,
            "access_count": 0,
        })
        self._save()
        return f"Remembered: {key}"

    def recall(self, query: str = "", category: str = "",
               limit: int = 20) -> str:
        """Search memories with optional category filter.

        Uses TF-IDF-like relevance when query is provided.
        """
        if not self.entries:
            return "(memory empty)"

        candidates = self.entries
        if category:
            candidates = [e for e in candidates if e.get("category") == category]

        if not query.strip():
            # No query: return recent entries
            recent = sorted(candidates, key=lambda e: e.get("updated", 0),
                            reverse=True)[:limit]
            return self._format_entries(recent)

        # TF-IDF search
        q_tokens = Counter(_tokenize(query))
        if not q_tokens:
            return "(empty query)"

        # Build document frequency
        all_docs = []
        for e in candidates:
            text = f"{e['key']} {e['value']}"
            all_docs.append(Counter(_tokenize(text)))

        df = Counter()
        for doc in all_docs:
            for term in doc:
                df[term] += 1
        n_docs = len(all_docs) or 1

        # Score each entry
        scored = []
        for e, doc in zip(candidates, all_docs):
            if not doc:
                continue
            # TF-IDF similarity
            score = 0.0
            doc_norm = 0.0
            for term, tf in doc.items():
                idf = math.log((1 + n_docs) / (1 + df.get(term, 0))) + 1
                tfidf = (tf / sum(doc.values())) * idf
                doc_norm += tfidf * tfidf
                if term in q_tokens:
                    score += tfidf * q_tokens[term]
            doc_norm = math.sqrt(doc_norm) or 1.0
            score = score / doc_norm

            # Boost recently accessed
            access_boost = 1.0 + 0.1 * min(e.get("access_count", 0), 10)
            score *= access_boost

            if score > 0.05:
                scored.append((e, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        matches = [e for e, s in scored[:limit]]
        if not matches:
            return f"(nothing matching '{query}')"

        # Mark as accessed
        for e in matches:
            e["accessed"] = time.time()
            e["access_count"] = e.get("access_count", 0) + 1
        self._save()

        return self._format_entries(matches)

    def context_block(self, limit: int = 10) -> str:
        """Recent memories as a prompt-injectable block."""
        if not self.entries:
            return ""
        recent = sorted(self.entries, key=lambda e: e.get("updated", 0),
                        reverse=True)[:limit]
        return "[REMEMBERED CONTEXT]\n" + self._format_entries(recent)

    def categories(self) -> dict[str, int]:
        """Count entries per category."""
        counts: dict[str, int] = {}
        for e in self.entries:
            cat = e.get("category", "fact")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def stats(self) -> str:
        """Memory statistics."""
        cats = self.categories()
        total = len(self.entries)
        lines = [f"Memory: {total} entries"]
        for cat, count in sorted(cats.items()):
            lines.append(f"  {cat}: {count}")
        if self.entries:
            oldest = min(e.get("created", 0) for e in self.entries)
            newest = max(e.get("updated", 0) for e in self.entries)
            if oldest:
                lines.append(
                    f"  Oldest: {time.strftime('%Y-%m-%d', time.localtime(oldest))}"
                )
            if newest:
                lines.append(
                    f"  Newest: {time.strftime('%Y-%m-%d', time.localtime(newest))}"
                )
        return "\n".join(lines)

    def _format_entries(self, entries: list[dict]) -> str:
        lines = []
        for e in entries:
            cat = e.get("category", "fact")
            key = e.get("key", "")
            value = e.get("value", "")
            lines.append(f"[{cat}] {key}: {value}")
        return "\n".join(lines)


MEMORY = Memory()
