"""Search tools: grep (content) aur find_files (glob)."""
from __future__ import annotations
import fnmatch
from pathlib import Path
from .base import Tool, walk_files


class Grep(Tool):
    name = "grep"
    description = (
        "File contents me text search karo. 'file:line: text' return karta hai. "
        "Optional 'ext' se ek extension tak seemit karo (e.g. '.py')."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text."},
                "ext": {"type": "string", "description": "Optional extension filter, e.g. '.py'."},
            },
            "required": ["query"],
        }

    def run(self, workdir: str, query: str, ext: str = "", **_) -> str:
        if not query:
            return "Error: empty query"
        root = Path(workdir).resolve()
        out, matches = [], 0
        for fp in walk_files(root):
            if ext and not fp.name.endswith(ext):
                continue
            try:
                with fp.open("r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if query in line:
                            out.append(f"{fp.relative_to(root)}:{i}: {line.strip()}")
                            matches += 1
                            if matches >= 200:
                                out.append("\n(stopped at 200 matches)")
                                return "\n".join(out)
            except Exception:
                continue
        return "\n".join(out) if out else "No matches found."


class FindFiles(Tool):
    name = "find_files"
    description = "Glob pattern se files dhoondho (e.g. '*.py', 'src/*.js')."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern."},
            },
            "required": ["pattern"],
        }

    def run(self, workdir: str, pattern: str, **_) -> str:
        if not pattern:
            return "Error: empty pattern"
        root = Path(workdir).resolve()
        out = []
        for fp in walk_files(root):
            rel = fp.relative_to(root)
            if fnmatch.fnmatch(fp.name, pattern) or fnmatch.fnmatch(str(rel), pattern):
                out.append(str(rel))
        return "\n".join(sorted(out)) if out else "No files found."
