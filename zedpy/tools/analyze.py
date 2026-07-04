"""Feature 8 — Python AST code analysis tool.

Real AST parsing (Python's `ast` module) se: functions, classes, imports,
unused imports, aur complexity estimate nikalta hai. Deep code intelligence.
"""
from __future__ import annotations
import ast
from pathlib import Path
from .base import Tool, safe_path, walk_files


class AnalyzeCode(Tool):
    name = "analyze_code"
    description = (
        "Python file/directory ka AST analysis: functions, classes, imports, "
        "unused imports, complexity. path = file ya dir (default: project root)."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Python file ya directory (optional)."},
            },
        }

    def run(self, workdir: str, path: str = ".", **_) -> str:
        target = safe_path(workdir, path or ".")
        files = []
        if target.is_file() and target.suffix == ".py":
            files = [target]
        elif target.is_dir():
            files = [f for f in walk_files(target) if f.suffix == ".py"]
        if not files:
            return "No Python files found."
        out = []
        for f in files[:50]:
            out.append(self._analyze(f, workdir))
        return "\n\n".join(out)

    @staticmethod
    def _analyze(f: Path, workdir: str) -> str:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src, filename=str(f))
        except SyntaxError as e:
            return f"📄 {f.name}: SyntaxError: {e}"
        funcs, classes, imports = [], [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                funcs.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                funcs.append(f"async {node.name}")
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                imports += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                imports += [f"{mod}.{a.name}" for a in node.names]
        # Unused imports (simple heuristic).
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        unused = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    name = (a.asname or a.name).split(".")[0]
                    if name not in used and name != "*":
                        unused.append(name)
        # Cyclomatic-ish complexity: count branch nodes.
        branches = sum(1 for n in ast.walk(tree)
                       if isinstance(n, (ast.If, ast.For, ast.While,
                                         ast.Try, ast.With, ast.BoolOp)))
        try:
            rel = f.relative_to(Path(workdir).resolve())
        except ValueError:
            rel = f.name
        lines = [f"📄 {rel}  ({len(src.splitlines())} lines, complexity~{branches})"]
        if classes:
            lines.append(f"   classes: {', '.join(classes[:15])}")
        if funcs:
            lines.append(f"   functions: {', '.join(funcs[:20])}")
        if unused:
            lines.append(f"   ⚠️ possibly unused imports: {', '.join(sorted(set(unused))[:10])}")
        return "\n".join(lines)
