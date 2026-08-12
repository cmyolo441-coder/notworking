"""Safe project file tools with atomic writes and undo integration."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ..core.undo import MANAGER as UNDO
from .base import MAX_TEXT_READ_BYTES, MAX_TEXT_WRITE_BYTES, Tool, safe_path


_BINARY_EXTENSIONS = {
    ".7z", ".avi", ".bin", ".bmp", ".class", ".dll", ".dylib", ".exe", ".gif",
    ".ico", ".jar", ".jpeg", ".jpg", ".mov", ".mp3", ".mp4", ".pdf", ".png",
    ".pyc", ".so", ".tar", ".wav", ".webp", ".woff", ".woff2", ".zip",
}


def _snapshot(p: Path, tool: str) -> None:
    UNDO.capture(str(p), tool)


def _commit() -> None:
    UNDO.commit()


def _looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:4096]


def _read_text(p: Path) -> str:
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise OSError(f"file stat nahi ho saka: {exc}") from exc
    if size > MAX_TEXT_READ_BYTES:
        raise ValueError(
            f"file bahut badi hai ({size} bytes); offset/limit ke saath smaller file chunks use karein"
        )
    raw = p.read_bytes()
    if _looks_binary(raw) or p.suffix.lower() in _BINARY_EXTENSIONS:
        raise ValueError(f"{p.name} binary file lagti hai; text read possible nahi")
    return raw.decode("utf-8", errors="replace")


def _atomic_write(p: Path, content: str) -> None:
    if not isinstance(content, str):
        raise TypeError("content string hona chahiye")
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_TEXT_WRITE_BYTES:
        raise ValueError(f"content limit {MAX_TEXT_WRITE_BYTES} bytes se zyada hai")
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = None
    if p.exists():
        mode = p.stat().st_mode & 0o777
    fd, temp_name = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp_name, mode)
        os.replace(temp_name, p)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


class ReadFile(Tool):
    name = "read_file"
    description = (
        "Ek UTF-8 text file ka content line numbers ke saath padho. Optional "
        "offset (0-indexed) aur limit se safe range padho."
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
        try:
            offset = max(0, int(offset or 0))
            limit = max(0, int(limit or 0))
        except (TypeError, ValueError):
            return "Error: offset aur limit integers hone chahiye"
        try:
            p = safe_path(workdir, path)
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        if not p.exists():
            return f"Error: file nahi mili: {path}"
        if p.is_dir():
            return f"Error: {path} ek directory hai, file nahi. list_dir use karo."
        try:
            data = _read_text(p)
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        lines = data.splitlines()
        start = min(offset, len(lines))
        end = min(start + limit, len(lines)) if limit else len(lines)
        out = [f"{i + 1}\t{lines[i]}" for i in range(start, end)]
        return "\n".join(out) if out else "(empty file or requested range empty)"


class WriteFile(Tool):
    name = "write_file"
    description = "Nayi UTF-8 text file banao ya poore content se safely overwrite karo."
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
        try:
            p = safe_path(workdir, path)
            existed = p.exists()
            _snapshot(p, "write_file")
            _atomic_write(p, content)
            _commit()
        except (OSError, TypeError, ValueError) as exc:
            return f"Error: write failed: {exc}"
        action = "Overwrote" if existed else "Created"
        return f"{action} {path} ({len(content.encode('utf-8'))} bytes, {content.count(chr(10)) + 1} lines)"


class AppendFile(Tool):
    name = "append_file"
    description = "UTF-8 text file ke end me content atomically append karo; file na ho to bana do."
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
        try:
            p = safe_path(workdir, path)
            existing = _read_text(p) if p.exists() else ""
            _snapshot(p, "append_file")
            _atomic_write(p, existing + content)
            _commit()
        except (OSError, TypeError, ValueError) as exc:
            return f"Error: append failed: {exc}"
        return f"Appended {len(content.encode('utf-8'))} bytes to {path}"


class EditFile(Tool):
    name = "edit_file"
    description = (
        "File me exact text replace karo. old_str exactly ek baar match hona "
        "chahiye; context add karke unique replacement do."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (project root relative)."},
                "old_str": {"type": "string", "description": "Exact unique text jo replace ho."},
                "new_str": {"type": "string", "description": "Replacement text."},
            },
            "required": ["path", "old_str", "new_str"],
        }

    def run(self, workdir: str, path: str, old_str: str, new_str: str, **_) -> str:
        try:
            p = safe_path(workdir, path)
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        if not p.exists():
            return f"Error: file nahi mili: {path}"
        try:
            content = _read_text(p)
        except (OSError, ValueError) as exc:
            return f"Error: edit failed: {exc}"
        count = content.count(old_str)
        if count == 0:
            return f"Error: old_str {path} me nahi mila. Pehle read_file se exact lines dekho."
        if count > 1:
            return f"Error: old_str {count} baar match hua; aur context add karke unique banao."
        try:
            _snapshot(p, "edit_file")
            _atomic_write(p, content.replace(old_str, new_str, 1))
            _commit()
        except (OSError, TypeError, ValueError) as exc:
            return f"Error: edit failed: {exc}"
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
        try:
            p = safe_path(workdir, path or ".")
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        if not p.is_dir():
            return f"Error: directory nahi hai: {path}"
        try:
            entries = sorted(
                (entry for entry in os.scandir(p) if not entry.is_symlink()),
                key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.casefold(), e.name),
            )
            rows = []
            for entry in entries[:500]:
                if entry.is_dir(follow_symlinks=False):
                    rows.append(f"{entry.name}/")
                else:
                    rows.append(f"{entry.name}  ({entry.stat(follow_symlinks=False).st_size} bytes)")
            if len(entries) > 500:
                rows.append(f"…[{len(entries) - 500} entries hidden]")
            return "\n".join(rows) if rows else "(empty directory)"
        except OSError as exc:
            return f"Error: directory read failed: {exc}"
