"""File tools: read_file, write_file, append_file, edit_file, list_dir.

Har mutating tool (write/append/edit) change se pehle ek in-memory snapshot
leta hai (undo ke liye) via the shared SNAPSHOTS list.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..core.undo import MANAGER as UNDO
from .base import Tool, safe_path


def _snapshot(p: Path, tool: str = "write"):
    """Change se pehle undo-manager me capture karo."""
    UNDO.capture(str(p), tool)


def _commit():
    UNDO.commit()


def _looks_binary(data: bytes) -> bool:
    chunk = data[:4096]
    return b"\x00" in chunk


class ReadFile(Tool):
    name = "read_file"
    description = (
        "Ek file ka content padho (line numbers ke saath). Optional 'offset' "
        "(0-indexed start line) aur 'limit' (kitni lines) se range padho."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (project root relative)."},
                "offset": {"type": "integer", "description": "Start line (0-indexed). Optional."},
                "limit": {"type": "integer", "description": "Kitni lines. Optional."},
            },
            "required": ["path"],
        }

    def run(self, workdir: str, path: str, offset: int = 0, limit: int = 0, **_) -> str:
        p = safe_path(workdir, path)
        if not p.exists():
            return f"Error: file nahi mili: {path}"
        if p.is_dir():
            return f"Error: {path} ek directory hai, file nahi. list_dir use karo."
        raw = p.read_bytes()
        if _looks_binary(raw):
            return f"{path} binary file lagti hai ({len(raw)} bytes). Text read possible nahi."
        data = raw.decode("utf-8", errors="replace")
        lines = data.split("\n")
        start = max(0, offset)
        end = start + limit if limit and limit > 0 else len(lines)
        end = min(end, len(lines))
        out = [f"{i + 1}\t{lines[i]}" for i in range(start, end)]
        return "\n".join(out) if out else "(empty file)"


class WriteFile(Tool):
    name = "write_file"
    description = "Nayi file banao ya poore content se overwrite karo."
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (project root relative)."},
                "content": {"type": "string", "description": "Poora file content."},
            },
            "required": ["path", "content"],
        }

    def run(self, workdir: str, path: str, content: str, **_) -> str:
        p = safe_path(workdir, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        _snapshot(p, "write_file")
        p.write_text(content, encoding="utf-8")
        _commit()
        action = "Overwrote" if existed else "Created"
        return f"{action} {path} ({len(content)} bytes, {content.count(chr(10)) + 1} lines)"


class AppendFile(Tool):
    name = "append_file"
    description = (
        "File ke end me content jodo (na ho to bana do). Bade file ko chhote "
        "chunks me banane ke liye: pehle write_file, phir append_file baar-baar."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (project root relative)."},
                "content": {"type": "string", "description": "Jo append karna hai."},
            },
            "required": ["path", "content"],
        }

    def run(self, workdir: str, path: str, content: str, **_) -> str:
        p = safe_path(workdir, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        _snapshot(p, "append_file")
        with p.open("a", encoding="utf-8") as fh:
            fh.write(content)
        _commit()
        return f"Appended {len(content)} bytes to {path}"


class EditFile(Tool):
    name = "edit_file"
    description = (
        "File me exact text replace karo. 'old_str' exactly ek baar match hona "
        "chahiye (context add karke unique banao). 'new_str' replacement."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (project root relative)."},
                "old_str": {"type": "string", "description": "Exact text jo replace ho (unique)."},
                "new_str": {"type": "string", "description": "Replacement text."},
            },
            "required": ["path", "old_str", "new_str"],
        }

    def run(self, workdir: str, path: str, old_str: str, new_str: str, **_) -> str:
        p = safe_path(workdir, path)
        if not p.exists():
            return f"Error: file nahi mili: {path}"
        content = p.read_text(encoding="utf-8", errors="replace")
        count = content.count(old_str)
        if count == 0:
            return (
                f"Error: old_str {path} me nahi mila. Pehle read_file se exact "
                "lines dekho ya chhota unique block do."
            )
        if count > 1:
            return f"Error: old_str {count} baar match hua; aur context add karke unique banao."
        _snapshot(p, "edit_file")
        p.write_text(content.replace(old_str, new_str, 1), encoding="utf-8")
        _commit()
        return f"Edited {path} (1 replacement)"


class ListDir(Tool):
    name = "list_dir"
    description = "Directory ke files/folders list karo (default: project root)."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (root relative). Optional."},
            },
        }

    def run(self, workdir: str, path: str = ".", **_) -> str:
        p = safe_path(workdir, path or ".")
        if not p.is_dir():
            return f"Error: directory nahi hai: {path}"
        rows = []
        for e in sorted(os.scandir(p), key=lambda e: (not e.is_dir(), e.name)):
            if e.is_dir():
                rows.append(f"{e.name}/")
            else:
                rows.append(f"{e.name}  ({e.stat().st_size} bytes)")
        return "\n".join(rows) if rows else "(empty directory)"
