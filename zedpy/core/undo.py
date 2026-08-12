"""Thread-safe undo/redo snapshots for project file mutations."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass


@dataclass
class Snapshot:
    path: str
    before: str | None
    after: str | None
    tool: str


class UndoManager:
    def __init__(self, max_depth: int = 100):
        self._undo: list[Snapshot] = []
        self._redo: list[Snapshot] = []
        self.max_depth = max(1, max_depth)
        self._lock = threading.RLock()
        self._pending = threading.local()

    @staticmethod
    def _read(path: str) -> str | None:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def capture(self, path: str, tool: str) -> None:
        """Capture the before-state; commit must be called after the mutation."""
        try:
            before = self._read(path)
        except OSError:
            before = None
        self._pending.snapshot = Snapshot(path=path, before=before, after=None, tool=tool)

    def commit(self) -> None:
        snap = getattr(self._pending, "snapshot", None)
        if snap is None:
            return
        try:
            snap.after = self._read(snap.path)
        except OSError:
            snap.after = None
        with self._lock:
            self._undo.append(snap)
            if len(self._undo) > self.max_depth:
                del self._undo[: len(self._undo) - self.max_depth]
            self._redo.clear()
        self._pending.snapshot = None

    def undo(self) -> str:
        with self._lock:
            if not self._undo:
                return "Nothing to undo."
            snap = self._undo.pop()
        try:
            self._restore(snap, to_before=True)
        except OSError as exc:
            with self._lock:
                self._undo.append(snap)
            return f"Error: undo failed: {exc}"
        with self._lock:
            self._redo.append(snap)
        return f"Undid change to {os.path.basename(snap.path)} ({snap.tool})"

    def redo(self) -> str:
        with self._lock:
            if not self._redo:
                return "Nothing to redo."
            snap = self._redo.pop()
        try:
            self._restore(snap, to_before=False)
        except OSError as exc:
            with self._lock:
                self._redo.append(snap)
            return f"Error: redo failed: {exc}"
        with self._lock:
            self._undo.append(snap)
        return f"Redid change to {os.path.basename(snap.path)} ({snap.tool})"

    @staticmethod
    def _restore(snap: Snapshot, to_before: bool) -> None:
        content = snap.before if to_before else snap.after
        if content is None:
            if os.path.exists(snap.path):
                os.remove(snap.path)
            return
        os.makedirs(os.path.dirname(snap.path) or ".", exist_ok=True)
        with open(snap.path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)

    def history(self) -> list[str]:
        with self._lock:
            return [
                f"{i + 1}. {snapshot.tool} {os.path.basename(snapshot.path)}"
                for i, snapshot in enumerate(self._undo)
            ]


# Shared manager used by file tools and slash commands.
MANAGER = UndoManager()
