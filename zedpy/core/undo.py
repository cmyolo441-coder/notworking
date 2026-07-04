"""Feature 3 — Undo/Redo system for file changes.

Har mutating tool (write/edit/append) change se pehle ek snapshot leta hai.
UndoManager in snapshots ko stack me rakhta hai; /undo aur /redo se revert hota hai.
"""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass
class Snapshot:
    path: str
    before: str | None  # None = file pehle exist nahi karti thi
    after: str | None
    tool: str


class UndoManager:
    def __init__(self, max_depth: int = 100):
        self._undo: list[Snapshot] = []
        self._redo: list[Snapshot] = []
        self.max_depth = max_depth

    def capture(self, path: str, tool: str) -> None:
        """Change se PEHLE call karo (before-content record hota hai)."""
        before = None
        if os.path.exists(path):
            try:
                before = open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                before = None
        self._pending = Snapshot(path=path, before=before, after=None, tool=tool)

    def commit(self) -> None:
        """Change ke BAAD call karo (after-content record + stack me push)."""
        snap = getattr(self, "_pending", None)
        if snap is None:
            return
        try:
            snap.after = open(snap.path, encoding="utf-8", errors="replace").read() \
                if os.path.exists(snap.path) else None
        except Exception:
            snap.after = None
        self._undo.append(snap)
        if len(self._undo) > self.max_depth:
            self._undo.pop(0)
        self._redo.clear()
        self._pending = None

    def undo(self) -> str:
        if not self._undo:
            return "Nothing to undo."
        snap = self._undo.pop()
        self._restore(snap, to_before=True)
        self._redo.append(snap)
        return f"Undid change to {os.path.basename(snap.path)} ({snap.tool})"

    def redo(self) -> str:
        if not self._redo:
            return "Nothing to redo."
        snap = self._redo.pop()
        self._restore(snap, to_before=False)
        self._undo.append(snap)
        return f"Redid change to {os.path.basename(snap.path)} ({snap.tool})"

    @staticmethod
    def _restore(snap: Snapshot, to_before: bool) -> None:
        content = snap.before if to_before else snap.after
        if content is None:
            if os.path.exists(snap.path):
                os.remove(snap.path)
        else:
            os.makedirs(os.path.dirname(snap.path) or ".", exist_ok=True)
            with open(snap.path, "w", encoding="utf-8") as f:
                f.write(content)

    def history(self) -> list[str]:
        return [f"{i+1}. {s.tool} {os.path.basename(s.path)}"
                for i, s in enumerate(self._undo)]


# Global instance jo tools use karte hain.
MANAGER = UndoManager()
