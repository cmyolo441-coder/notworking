"""Advanced project tools: diffs, scaffolding, HTTP, data, regex and tree."""
from __future__ import annotations

import difflib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ..core.undo import MANAGER as UNDO
from .base import MAX_TEXT_READ_BYTES, Tool, safe_path
from .files import _atomic_write, _read_text

_MAX_DIFF_LINES = 200
_MAX_TREE_ENTRIES = 100
_MAX_HTTP_BYTES = 200 * 1024
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,47}$")


class ShowDiff(Tool):
    name = "show_diff"
    description = "Unified diff between a file's current content and proposed new content."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "File path."},
            "new_content": {"type": "string", "description": "Proposed new content."}},
            "required": ["path", "new_content"]}

    def run(self, workdir: str, path: str, new_content: str, **_) -> str:
        try:
            p = safe_path(workdir, path)
            old = _read_text(p) if p.exists() else ""
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        if len((new_content or "").encode("utf-8")) > MAX_TEXT_READ_BYTES:
            return "Error: proposed content too large"
        diff = difflib.unified_diff(
            old.splitlines(), (new_content or "").splitlines(),
            fromfile=f"{path} (old)", tofile=f"{path} (new)", lineterm="",
        )
        lines = list(diff)
        if not lines:
            return "No differences."
        added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        return f"(+{added} -{removed})\n" + "\n".join(lines[:_MAX_DIFF_LINES])


class Scaffold(Tool):
    name = "scaffold"
    description = "Create a project template. kind = python|flask|cli. name = project folder name."
    requires_approval = True

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

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "kind": {"type": "string", "description": "python|flask|cli"},
            "name": {"type": "string", "description": "Project name."}},
            "required": ["kind", "name"]}

    def run(self, workdir: str, kind: str, name: str, **_) -> str:
        kind = (kind or "").strip().lower()
        name = (name or "").strip()
        template = self._TEMPLATES.get(kind)
        if not template:
            return f"Unknown kind '{kind}'. Options: {', '.join(self._TEMPLATES)}"
        if not _NAME_RE.fullmatch(name):
            return "Error: name must start with a letter and contain only letters, numbers, '_' or '-'."
        created = []
        try:
            for relative, content in template.items():
                relative = relative.format(name=name)
                file_path = safe_path(workdir, relative)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                UNDO.capture(str(file_path), "scaffold")
                _atomic_write(file_path, content.format(name=name))
                UNDO.commit()
                created.append(relative)
        except (OSError, ValueError) as exc:
            return f"Error: scaffold failed: {exc}"
        return f"Scaffolded '{kind}' project:\n" + "\n".join(f"  + {item}" for item in created)


class HttpRequest(Tool):
    name = "http_request"
    description = "Make an approved HTTP request. method=GET/POST, url, body (optional JSON string), headers (optional)."
    requires_approval = True

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "method": {"type": "string", "description": "GET/POST/PUT/DELETE"},
            "url": {"type": "string", "description": "Full http(s) URL."},
            "body": {"type": "string", "description": "Request body (optional)."},
            "headers": {"type": "object", "description": "Headers (optional)."}},
            "required": ["url"]}

    def run(self, workdir: str, url: str, method: str = "GET", body: str = "",
            headers: dict | None = None, **_) -> str:
        parsed = urlparse((url or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "Error: only valid http:// or https:// URLs are allowed"
        if parsed.username or parsed.password:
            return "Error: URLs with embedded credentials are not allowed"
        method = (method or "GET").upper().strip()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            return f"Error: unsupported HTTP method: {method}"
        if len((body or "").encode("utf-8")) > MAX_HTTP_BYTES:
            return "Error: request body too large"
        safe_headers = {str(k): str(v) for k, v in (headers or {}).items() if str(k).lower() != "host"}
        try:
            request = urllib.request.Request(
                parsed.geturl(), data=body.encode("utf-8") if body else None,
                method=method, headers=safe_headers,
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(MAX_HTTP_BYTES + 1)
                truncated = len(payload) > MAX_HTTP_BYTES
                text = payload[:MAX_HTTP_BYTES].decode("utf-8", errors="replace")
                suffix = "\n…[response truncated]" if truncated else ""
                return f"HTTP {response.status}\n{text[:8000]}{suffix}"
        except urllib.error.HTTPError as exc:
            detail = exc.read(2000).decode("utf-8", errors="replace")
            return f"HTTP {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return f"Error: HTTP request failed: {exc}"


class DataTool(Tool):
    name = "data_tool"
    description = "Parse/validate/query JSON. action=validate|keys|get. path=file. key=dotted path (for get)."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "action": {"type": "string", "description": "validate|keys|get"},
            "path": {"type": "string", "description": "JSON file path."},
            "key": {"type": "string", "description": "Dotted key path e.g. 'a.b.0' (for get)."}},
            "required": ["action", "path"]}

    def run(self, workdir: str, action: str, path: str, key: str = "", **_) -> str:
        try:
            file_path = safe_path(workdir, path)
            if not file_path.exists() or not file_path.is_file():
                return f"Error: not found: {path}"
            data = json.loads(_read_text(file_path))
        except json.JSONDecodeError as exc:
            return f"Invalid JSON: {exc}"
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        action = (action or "").lower().strip()
        if action == "validate":
            return f"Valid JSON ({type(data).__name__})"
        if action == "keys":
            if isinstance(data, dict):
                return "Keys: " + ", ".join(str(item) for item in list(data)[:50])
            return f"Top-level is {type(data).__name__}, length {len(data) if hasattr(data, '__len__') else '?'}"
        if action == "get":
            if not key:
                return "Error: key required for get"
            current = data
            try:
                for part in key.split("."):
                    if not part:
                        continue
                    current = current[int(part)] if isinstance(current, list) else current[part]
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                return f"Error: key path not found: {key} ({exc})"
            return json.dumps(current, ensure_ascii=False, indent=2)[:4000]
        return f"Unknown action: {action}. Use validate, keys or get."


class RegexReplace(Tool):
    name = "regex_replace"
    description = "Regex search & replace in a UTF-8 text file. pattern, replacement, path. Returns count + preview."
    requires_approval = True

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "File path."},
            "pattern": {"type": "string", "description": "Regex pattern."},
            "replacement": {"type": "string", "description": "Replacement (supports \\1 groups)."}},
            "required": ["path", "pattern", "replacement"]}

    def run(self, workdir: str, path: str, pattern: str, replacement: str, **_) -> str:
        try:
            file_path = safe_path(workdir, path)
            if not file_path.exists():
                return f"Error: not found: {path}"
            content = _read_text(file_path)
            new_content, count = re.subn(pattern, replacement, content)
        except re.error as exc:
            return f"Error: bad regex: {exc}"
        except (OSError, ValueError) as exc:
            return f"Error: regex replace failed: {exc}"
        if count == 0:
            return "No matches — file unchanged."
        try:
            UNDO.capture(str(file_path), "regex_replace")
            _atomic_write(file_path, new_content)
            UNDO.commit()
        except (OSError, ValueError) as exc:
            return f"Error: regex replace failed: {exc}"
        return f"Replaced {count} occurrence(s) in {path}."


class Tree(Tool):
    name = "tree"
    description = "Show the project directory tree structure (like the `tree` command)."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory (optional)."},
            "max_depth": {"type": "integer", "description": "Max depth (default 3)."}}}

    def run(self, workdir: str, path: str = ".", max_depth: int = 3, **_) -> str:
        from .base import SKIP_DIRS
        try:
            root = safe_path(workdir, path or ".")
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"
        if not root.is_dir():
            return f"Error: directory nahi hai: {path}"
        max_depth = max(0, min(int(max_depth or 3), 20))
        output = [root.name + "/"]
        count = 0

        def walk(directory: Path, prefix: str, depth: int) -> None:
            nonlocal count
            if depth > max_depth or count >= _MAX_TREE_ENTRIES:
                return
            try:
                entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
            except OSError:
                return
            entries = [
                item for item in entries
                if item.name not in SKIP_DIRS and not item.name.startswith(".") and not item.is_symlink()
            ]
            for index, item in enumerate(entries):
                if count >= _MAX_TREE_ENTRIES:
                    output.append(prefix + "└── …[entry limit]")
                    return
                count += 1
                last = index == len(entries) - 1
                output.append(f"{prefix}{'└── ' if last else '├── '}{item.name}{'/' if item.is_dir() else ''}")
                if item.is_dir():
                    walk(item, prefix + ("    " if last else "│   "), depth + 1)

        walk(root, "", 1)
        return "\n".join(output)
