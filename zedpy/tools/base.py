"""Base tool class + shared helpers (path safety, skip dirs)."""
from __future__ import annotations
import os
from pathlib import Path

# Bade / generated directories jinko search/walk skip karega.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", ".idea", ".cache", ".next", ".nuxt", "out", "coverage",
}


class Tool:
    """Sabhi tools ka base. Subclass name/description/parameters/run set kare."""

    name: str = ""
    description: str = ""
    requires_approval: bool = False  # write/edit/shell -> True

    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    def run(self, workdir: str, **kwargs) -> str:
        raise NotImplementedError

    def schema(self) -> dict:
        """OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters(),
            },
        }


def safe_path(workdir: str, rel: str) -> Path:
    """`rel` ko workdir ke andar resolve karo; bahar jaane par ValueError.

    Path-traversal (../../) attacks se bachata hai.
    """
    root = Path(workdir).resolve()
    target = (root / (rel or ".")).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"path {rel!r} working directory ke bahar hai — allowed nahi")
    return target


def walk_files(root: Path):
    """Skip-dirs ko chhod kar saari files par iterate karo."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield Path(dirpath) / f
