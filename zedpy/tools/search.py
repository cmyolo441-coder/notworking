from __future__ import annotations

import fnmatch
from pathlib import Path

from .base import Tool, walk_files, safe_path

_MAX_MATCHES = 200
_MAX_OUTPUT_CHARS = 24_000


class Grep(Tool):
    name = "grep"
    description = (
        "Project text files me literal text search karo. file:line: text results "
        "return hote hain; optional ext aur case_sensitive filters available hain."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text."},
                "ext": {"type": "string", "description": "Optional extension, e.g. .py."},
                "case_sensitive": {"type": "boolean", "description": "Default false."},
            },
            "required": ["query"],
        }

    def run(self, workdir: str, query: str, ext: str = "", case_sensitive: bool = False, **_) -> str:
        query = query or ""
        if not query.strip():
            return "Error: empty query"
        try:
            root = safe_path(workdir, ".")
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        extension = (ext or "").strip().lower()
        if extension and not extension.startswith("."):
            extension = "." + extension
        needle = query if case_sensitive else query.casefold()
        out: list[str] = []
        matches = 0
        chars = 0
        for file_path in walk_files(root):
            if extension and file_path.suffix.lower() != extension:
                continue
            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, 1):
                        haystack = line if case_sensitive else line.casefold()
                        if needle not in haystack:
                            continue
                        row = f"{file_path.relative_to(root).as_posix()}:{line_number}: {line.rstrip()}"
                        if chars + len(row) > _MAX_OUTPUT_CHARS:
                            out.append("\n(stopped: output limit reached)")
                            return "\n".join(out)
                        out.append(row)
                        chars += len(row)
                        matches += 1
                        if matches >= _MAX_MATCHES:
                            out.append(f"\n(stopped at {_MAX_MATCHES} matches)")
                            return "\n".join(out)
            except (OSError, UnicodeError):
                continue
        return "\n".join(out) if out else "No matches found."


class FindFiles(Tool):
    name = "find_files"
    description = "Project ke andar glob pattern se files dhoondho (e.g. '*.py', 'src/*.js')."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"pattern": {"type": "string", "description": "Glob pattern."}},
            "required": ["pattern"],
        }

    def run(self, workdir: str, pattern: str, **_) -> str:
        pattern = (pattern or "").strip()
        if not pattern:
            return "Error: empty pattern"
        try:
            root = safe_path(workdir, ".")
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        normalized = pattern.replace("\\", "/")
        matches = []
        for file_path in walk_files(root):
            rel = file_path.relative_to(root).as_posix()
            if fnmatch.fnmatch(file_path.name, normalized) or fnmatch.fnmatch(rel, normalized):
                matches.append(rel)
        return "\n".join(matches) if matches else "No files found."
