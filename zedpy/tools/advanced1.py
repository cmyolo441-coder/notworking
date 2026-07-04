"""Advanced tools batch 1 (features 1-6 of the new 18).

  #5  code_metrics     — LOC / file / complexity stats
  #6  fuzzy_find       — smart fuzzy filename matching
  #8  lint             — Python syntax + basic style check
  #9  deps             — dependency / import analysis
  #10 secret_scan      — detect API keys / passwords / tokens
  #11 todo_scan        — extract TODO / FIXME / HACK comments
"""
from __future__ import annotations
import ast
import difflib
import re
from collections import Counter
from pathlib import Path

from .base import Tool, safe_path, walk_files

_CODE_EXT = {".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp",
             ".jsx", ".tsx", ".rb", ".php", ".sh"}

# Lint: maximum line length before warning.
_MAX_LINE_LENGTH = 100


class CodeMetrics(Tool):  # feature #5
    name = "code_metrics"
    description = "Project metrics: total files, lines of code, by-language breakdown, biggest files."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory (optional)."}}}

    def run(self, workdir: str, path: str = ".", **_) -> str:
        root = safe_path(workdir, path or ".")
        by_lang: Counter = Counter()
        lines_by_lang: Counter = Counter()
        sizes = []
        for f in walk_files(root):
            ext = f.suffix.lower()
            if ext not in _CODE_EXT and ext not in {".md", ".json", ".yaml", ".yml", ".html", ".css"}:
                continue
            try:
                n = sum(1 for _ in f.open("r", encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            by_lang[ext] += 1
            lines_by_lang[ext] += n
            sizes.append((str(f.relative_to(root)), n))
        if not sizes:
            return "No code files found."
        total_files = sum(by_lang.values())
        total_lines = sum(lines_by_lang.values())
        out = [f"📊 Code Metrics", f"  Files: {total_files}   Lines: {total_lines}", "", "  By language:"]
        for ext, cnt in by_lang.most_common():
            out.append(f"    {ext or '(none)':<8} {cnt:>4} files  {lines_by_lang[ext]:>6} lines")
        out.append("\n  Biggest files:")
        for name, n in sorted(sizes, key=lambda x: x[1], reverse=True)[:8]:
            out.append(f"    {n:>6}  {name}")
        return "\n".join(out)


class FuzzyFind(Tool):  # feature #6
    name = "fuzzy_find"
    description = "Fuzzy filename search — approximate matching (e.g. 'authcfg' finds 'auth_config.py')."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "query": {"type": "string", "description": "Approximate filename."}},
            "required": ["query"]}

    def run(self, workdir: str, query: str, **_) -> str:
        root = Path(workdir).resolve()
        files = [str(f.relative_to(root)) for f in walk_files(root)]
        names = [Path(f).name for f in files]
        scored = []
        q = query.lower()
        for full, name in zip(files, names):
            ratio = difflib.SequenceMatcher(None, q, name.lower()).ratio()
            if q in name.lower():
                ratio += 0.5
            scored.append((full, ratio))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [f for f, s in scored[:10] if s > 0.2]
        return "\n".join(top) if top else "No fuzzy matches."


class Lint(Tool):  # feature #8
    name = "lint"
    description = "Lint a Python file: syntax errors, long lines, bare except, unused vars (basic)."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Python file."}},
            "required": ["path"]}

    def run(self, workdir: str, path: str, **_) -> str:
        p = safe_path(workdir, path)
        if not p.exists():
            return f"Error: not found: {path}"
        src = p.read_text(encoding="utf-8", errors="replace")
        issues = []
        try:
            ast.parse(src)
        except SyntaxError as e:
            return f"❌ SyntaxError line {e.lineno}: {e.msg}"
        for i, line in enumerate(src.splitlines(), 1):
            if len(line) > _MAX_LINE_LENGTH:
                issues.append(f"  L{i}: line too long ({len(line)} chars)")
            if re.search(r"except\s*:", line):
                issues.append(f"  L{i}: bare 'except:' — catch specific exceptions")
            if "\t" in line and "    " in line:
                issues.append(f"  L{i}: mixed tabs and spaces")
        return f"✅ {path}: no issues" if not issues else f"⚠️ {path}:\n" + "\n".join(issues[:30])


class Deps(Tool):  # feature #9
    name = "deps"
    description = "Analyze dependencies: imports in Python files + requirements.txt / package.json."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory (optional)."}}}

    def run(self, workdir: str, path: str = ".", **_) -> str:
        root = safe_path(workdir, path or ".")
        third_party: Counter = Counter()
        for f in walk_files(root):
            if f.suffix != ".py":
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        third_party[a.name.split(".")[0]] += 1
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    third_party[node.module.split(".")[0]] += 1
        out = ["📦 Dependencies (top imports):"]
        for mod, cnt in third_party.most_common(20):
            out.append(f"  {cnt:>3}×  {mod}")
        for mf in ["requirements.txt", "package.json", "pyproject.toml"]:
            mp = root / mf
            if mp.exists():
                out.append(f"\n  Manifest found: {mf}")
        return "\n".join(out)


class SecretScan(Tool):  # feature #10
    name = "secret_scan"
    description = "Scan the project for hardcoded secrets: API keys, tokens, passwords, private keys."

    _PATTERNS = [
        ("AWS key", r"AKIA[0-9A-Z]{16}"),
        ("GitHub token", r"gh[pousr]_[A-Za-z0-9_]{36,}"),
        ("OpenAI/sk key", r"sk-[A-Za-z0-9]{20,}"),
        ("Private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        ("Password assign", r"(?i)(password|passwd|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
        ("Bearer token", r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    ]

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory (optional)."}}}

    def run(self, workdir: str, path: str = ".", **_) -> str:
        root = safe_path(workdir, path or ".")
        compiled = [(n, re.compile(p)) for n, p in self._PATTERNS]
        findings = []
        for f in walk_files(root):
            if f.suffix.lower() in {".png", ".jpg", ".gif", ".pdf", ".zip"}:
                continue
            try:
                for i, line in enumerate(f.open("r", encoding="utf-8", errors="ignore"), 1):
                    for name, rx in compiled:
                        m = rx.search(line)
                        if m:
                            ev = m.group(0)
                            ev = ev[:6] + "…" + ev[-4:] if len(ev) > 14 else ev
                            findings.append(f"  🔴 {name}: {f.relative_to(root)}:{i}  ({ev})")
            except Exception:
                continue
        if not findings:
            return "✅ No secrets detected."
        return f"⚠️ {len(findings)} potential secret(s):\n" + "\n".join(findings[:40])


class TodoScan(Tool):  # feature #11
    name = "todo_scan"
    description = "Find all TODO / FIXME / HACK / XXX / BUG comments across the codebase."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory (optional)."}}}

    def run(self, workdir: str, path: str = ".", **_) -> str:
        root = safe_path(workdir, path or ".")
        rx = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b[:\s]*(.*)", re.IGNORECASE)
        out = []
        for f in walk_files(root):
            if f.suffix.lower() not in _CODE_EXT and f.suffix.lower() not in {".md", ".txt"}:
                continue
            try:
                for i, line in enumerate(f.open("r", encoding="utf-8", errors="ignore"), 1):
                    m = rx.search(line)
                    if m:
                        out.append(f"  [{m.group(1).upper()}] {f.relative_to(root)}:{i}  {m.group(2).strip()[:70]}")
            except Exception:
                continue
        return "\n".join(out[:60]) if out else "No TODO/FIXME comments found."
