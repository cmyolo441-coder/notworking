"""Feature 1 — Session persistence.

Conversations ko disk par save karta hai (JSON) taaki restart ke baad resume ho.
Files ~/.zedpy/sessions/ me store hoti hain, ek file per session.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


def _sessions_dir() -> Path:
    d = Path(os.path.expanduser("~/.zedpy/sessions"))
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Session:
    id: str
    title: str
    model: str
    workdir: str
    created: float
    updated: float
    messages: list[dict] = field(default_factory=list)

    @classmethod
    def new(cls, model: str, workdir: str) -> "Session":
        ts = time.time()
        sid = time.strftime("%Y%m%d-%H%M%S", time.localtime(ts))
        return cls(id=sid, title="(new session)", model=model,
                   workdir=workdir, created=ts, updated=ts, messages=[])

    def path(self) -> Path:
        return _sessions_dir() / f"{self.id}.json"

    def save(self) -> None:
        self.updated = time.time()
        # Title = pehla real user message (system prompt chhod ke).
        for m in self.messages:
            if m.get("role") == "user" and not m["content"].startswith("["):
                self.title = m["content"][:50]
                break
        self.path().write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                               encoding="utf-8")

    @classmethod
    def load(cls, sid: str) -> "Session | None":
        p = _sessions_dir() / f"{sid}.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(**data)

    @staticmethod
    def list_all() -> list[dict]:
        """Metadata of all saved sessions, newest first."""
        out = []
        for p in _sessions_dir().glob("*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                out.append({"id": d["id"], "title": d.get("title", ""),
                            "updated": d.get("updated", 0),
                            "messages": len(d.get("messages", []))})
            except Exception:
                continue
        return sorted(out, key=lambda x: x["updated"], reverse=True)

    @staticmethod
    def latest() -> "Session | None":
        allm = Session.list_all()
        return Session.load(allm[0]["id"]) if allm else None
