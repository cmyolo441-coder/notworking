"""Advanced tools batch 2 (more of the new 18).

  #2  show_diff        — colored unified diff between two contents/files
  #12 scaffold         — create project templates
  #13 http_request     — make HTTP API calls
  #14 data_tool        — parse/query/validate JSON & YAML
  #15 regex_replace    — regex search & replace across files
  #16 tree             — visualize project structure
"""
from __future__ import annotations
import difflib
import json
import re
import urllib.request
from pathlib import Path

from .base import Tool, safe_path, walk_files
from ..core.undo import MANAGER as UNDO

# ShowDiff: max diff lines to display.
_MAX_DIFF_LINES = 200
# Scaffold: max tree entries to show.
_MAX_TREE_ENTRIES = 100


class ShowDiff(Tool):  # feature #2
    name = "show_diff"
    description = "Unified diff between a file's current content and proposed new content."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "File path."},
            "new_content": {"type": "string", "description": "Proposed new content."}},
            "required": ["path", "new_content"]}

    def run(self, workdir: str, path: str, new_content: str, **_) -> str:
        p = safe_path(workdir, path)
        old = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        diff = difflib.unified_diff(old.splitlines(), new_content.splitlines(),
                                    fromfile=f"{path} (old)", tofile=f"{path} (new)",
                                    lineterm="")
        lines = list(diff)
        if not lines:
            return "No differences."
        add = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        rem = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
        return f"(+{add} -{rem})\n" + "\n".join(lines[:_MAX_DIFF_LINES])


class Scaffold(Tool):  # feature #12
    name = "scaffold"
    description = "Create a project template. kind = python|flask|cli. name = project folder name."

    _TEMPLATES = {
        "python": {
            "{name}/__init__.py": "",
            "{name}/main.py": 'def main():\n    print("Hello from {name}")\n\n\nif __name__ == "__main__":\n    main()\n',
            "tests/test_main.py": "def test_placeholder():\n    assert True\n",
            "README.md": "# {name}\n\nA Python project.\n",
            "requirements.txt": "",
        },
        "flask": {
            "app.py": 'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/")\ndef home():\n    return "Hello from {name}"\n\nif __name__ == "__main__":\n    app.run(debug=True)\n',
            "requirements.txt": "flask\n",
            "README.md": "# {name}\n\nA Flask app. Run: `python app.py`\n",
        },
        "cli": {
            "{name}.py": 'import argparse\n\ndef main():\n    p = argparse.ArgumentParser(prog="{name}")\n    p.add_argument("input")\n    args = p.parse_args()\n    print(args.input)\n\nif __name__ == "__main__":\n    main()\n',
            "README.md": "# {name} CLI\n",
        },
    }

    requires_approval = True

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "kind": {"type": "string", "description": "python|flask|cli"},
            "name": {"type": "string", "description": "Project name."}},
            "required": ["kind", "name"]}

    def run(self, workdir: str, kind: str, name: str, **_) -> str:
        tpl = self._TEMPLATES.get(kind)
        if not tpl:
            return f"Unknown kind '{kind}'. Options: {', '.join(self._TEMPLATES)}"
        created = []
        for rel, content in tpl.items():
            rel = rel.format(name=name)
            fp = safe_path(workdir, rel)
            fp.parent.mkdir(parents=True, exist_ok=True)
            UNDO.capture(str(fp), "scaffold")
            fp.write_text(content.format(name=name), encoding="utf-8")
            UNDO.commit()
            created.append(rel)
        return f"Scaffolded '{kind}' project:\n" + "\n".join(f"  + {c}" for c in created)


class HttpRequest(Tool):  # feature #13
    name = "http_request"
    description = "Make an HTTP request. method=GET/POST, url, body (optional JSON string), headers (optional)."

    requires_approval = True

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "method": {"type": "string", "description": "GET/POST/PUT/DELETE"},
            "url": {"type": "string", "description": "Full URL."},
            "body": {"type": "string", "description": "Request body (optional)."},
            "headers": {"type": "object", "description": "Headers (optional)."}},
            "required": ["url"]}

    def run(self, workdir: str, url: str, method: str = "GET", body: str = "",
            headers: dict | None = None, **_) -> str:
        try:
            data = body.encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data, method=method.upper(),
                                         headers=headers or {})
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read(200 * 1024).decode("utf-8", errors="replace")
                return f"HTTP {r.status}\n{text[:8000]}"
        except Exception as e:
            return f"Error: {e}"


class DataTool(Tool):  # feature #14
    name = "data_tool"
    description = "Parse/validate/query JSON. action=validate|keys|get. path=file. key=dotted path (for get)."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "action": {"type": "string", "description": "validate|keys|get"},
            "path": {"type": "string", "description": "JSON file path."},
            "key": {"type": "string", "description": "Dotted key path e.g. 'a.b.0' (for get)."}},
            "required": ["action", "path"]}

    def run(self, workdir: str, action: str, path: str, key: str = "", **_) -> str:
        p = safe_path(workdir, path)
        if not p.exists():
            return f"Error: not found: {path}"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return f"❌ Invalid JSON: {e}"
        if action == "validate":
            return f"✅ Valid JSON ({type(data).__name__})"
        if action == "keys":
            if isinstance(data, dict):
                return "Keys: " + ", ".join(list(data.keys())[:50])
            return f"Top-level is {type(data).__name__}, length {len(data) if hasattr(data,'__len__') else '?'}"
        if action == "get":
            cur = data
            for part in key.split("."):
                if part == "":
                    continue
                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
            return json.dumps(cur, ensure_ascii=False, indent=2)[:4000]
        return f"Unknown action: {action}"


class RegexReplace(Tool):  # feature #15
    name = "regex_replace"
    description = "Regex search & replace in a file. pattern, replacement, path. Returns count + preview."

    requires_approval = True

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "File path."},
            "pattern": {"type": "string", "description": "Regex pattern."},
            "replacement": {"type": "string", "description": "Replacement (supports \\1 groups)."}},
            "required": ["path", "pattern", "replacement"]}

    def run(self, workdir: str, path: str, pattern: str, replacement: str, **_) -> str:
        p = safe_path(workdir, path)
        if not p.exists():
            return f"Error: not found: {path}"
        content = p.read_text(encoding="utf-8", errors="replace")
        try:
            new, n = re.subn(pattern, replacement, content)
        except re.error as e:
            return f"Error: bad regex: {e}"
        if n == 0:
            return "No matches — file unchanged."
        UNDO.capture(str(p), "regex_replace")
        p.write_text(new, encoding="utf-8")
        UNDO.commit()
        return f"Replaced {n} occurrence(s) in {path}."


class Tree(Tool):  # feature #16
    name = "tree"
    description = "Show the project directory tree structure (like the `tree` command)."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory (optional)."},
            "max_depth": {"type": "integer", "description": "Max depth (default 3)."}}}

    def run(self, workdir: str, path: str = ".", max_depth: int = 3, **_) -> str:
        from .base import SKIP_DIRS
        root = safe_path(workdir, path or ".")
        out = [root.name + "/"]

        def walk(d: Path, prefix: str, depth: int):
            if depth > max_depth:
                return
            try:
                entries = sorted(d.iterdir(), key=lambda e: (e.is_file(), e.name))
            except Exception:
                return
            entries = [e for e in entries if e.name not in SKIP_DIRS and not e.name.startswith(".")]
            for i, e in enumerate(entries[:40]):
                last = i == len(entries) - 1
                out.append(f"{prefix}{'└── ' if last else '├── '}{e.name}{'/' if e.is_dir() else ''}")
                if e.is_dir():
                    walk(e, prefix + ("    " if last else "│   "), depth + 1)

        walk(root, "", 1)
        return "\n".join(out[:100])
