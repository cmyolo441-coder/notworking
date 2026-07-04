"""Feature 2 — Codebase index + TF-IDF semantic search.

Project ki text files ko index karta hai aur ek query ke liye sabse relevant
files rank karta hai (TF-IDF cosine similarity). Auto-context ke liye use hota hai.
Pure standard library — koi numpy/sklearn nahi.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from pathlib import Path

from ..tools.base import walk_files

_TEXT_EXT = {".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp", ".h",
             ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh", ".html",
             ".css", ".jsx", ".tsx", ".rb", ".php"}
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class CodeIndex:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.docs: dict[str, Counter] = {}   # relpath -> term counts
        self.df: Counter = Counter()          # document frequency
        self.n_docs = 0
        self.built = False

    def build(self, max_files: int = 2000, max_bytes: int = 512 * 1024) -> dict:
        self.docs.clear()
        self.df.clear()
        count = 0
        for fp in walk_files(self.root):
            if fp.suffix.lower() not in _TEXT_EXT:
                continue
            try:
                if fp.stat().st_size > max_bytes:
                    continue
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            toks = _tokenize(text)
            if not toks:
                continue
            tf = Counter(toks)
            rel = str(fp.relative_to(self.root))
            self.docs[rel] = tf
            for term in set(toks):
                self.df[term] += 1
            count += 1
            if count >= max_files:
                break
        self.n_docs = count
        self.built = True
        return {"files": count, "terms": len(self.df)}

    def _idf(self, term: str) -> float:
        return math.log((1 + self.n_docs) / (1 + self.df.get(term, 0))) + 1

    def _vec(self, tf: Counter) -> dict[str, float]:
        return {t: (c / sum(tf.values())) * self._idf(t) for t, c in tf.items()}

    def search(self, query: str, limit: int = 5) -> list[tuple[str, float]]:
        if not self.built:
            self.build()
        q_tf = Counter(_tokenize(query))
        if not q_tf:
            return []
        q_vec = self._vec(q_tf)
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        scored = []
        for rel, tf in self.docs.items():
            d_vec = self._vec(tf)
            dot = sum(q_vec.get(t, 0) * v for t, v in d_vec.items())
            d_norm = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0
            score = dot / (q_norm * d_norm)
            if score > 0:
                scored.append((rel, round(score, 4)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]
