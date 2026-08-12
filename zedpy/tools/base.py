from __future__ import annotations

import os
from pathlib import Path

# Generated and dependency directories that are intentionally excluded from
# project-wide scans. Keeping this list centralized prevents each tool from
# implementing subtly different traversal rules.
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".zedpy", "node_modules", "__pycache__", ".venv",
    "venv", "env", "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", ".idea", ".cache", ".next", ".nuxt", "out", "coverage",
}

MAX_TEXT_READ_BYTES = 8 * 1024 * 1024
MAX_TEXT_WRITE_BYTES = 16 * 1024 * 1024


class Tool:
    """Common interface for all agent tools."""

    name: str = ""
    description: str = ""
    requires_approval: bool = False

    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    def run(self, workdir: str, **kwargs) -> str:
        raise NotImplementedError

    def schema(self) -> dict:
        """Return an OpenAI-compatible function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters(),
            },
        }


def safe_path(workdir: str, rel: str) -> Path:
    """Resolve *rel* inside *workdir* and reject traversal/symlink escapes.

    Both the requested path and existing parent symlinks are resolved before the
    containment check. This protects tools from ``..`` traversal as well as a
    seemingly innocent path that points through a symlink outside the workdir.
    """
    if "\x00" in (rel or ""):
        raise ValueError("path me NUL byte allowed nahi hai")
    root = Path(workdir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"working directory directory nahi hai: {workdir}")
    target = (root / (rel or ".")).resolve(strict=False)
    if target != root and root not in target.parents:
        raise ValueError(f"path {rel!r} working directory ke bahar hai — allowed nahi")
    return target


def walk_files(root: Path):
    """Yield regular files under *root* in deterministic order.

    Hidden/generated directories and symlinked files are skipped. Skipping
    symlinked files avoids reading or mutating content outside the workdir.
    """
    root = Path(root).resolve()
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not (Path(dirpath) / d).is_symlink()
        )
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.is_symlink() or not path.is_file():
                continue
            yield path
