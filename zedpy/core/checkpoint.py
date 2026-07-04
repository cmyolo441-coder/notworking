"""Feature #7 — Project checkpoints (full snapshot + restore).

Poore project ka ek named snapshot (text files) leta hai aur baad me restore
kar sakta hai. Undo se alag: ye entire-project level pe hai. Stored in .zedpy/checkpoints/.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..tools.base import walk_files

_TEXT_EXT = {".py", ".js", ".ts", ".go", ".md", ".txt", ".json", ".yaml",
             ".yml", ".toml", ".html", ".css", ".sh", ".rs", ".c", ".cpp"}


def _ckpt_dir(workdir: str) -> Path:
    d = Path(workdir) / ".zedpy" / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create(workdir: str, name: str = "") -> str:
    root = Path(workdir).resolve()
    name = name or time.strftime("ckpt-%Y%m%d-%H%M%S")
    snap = {"name": name, "created": time.time(), "files": {}}
    count = 0
    for f in walk_files(root):
        if f.suffix.lower() not in _TEXT_EXT:
            continue
        try:
            if f.stat().st_size > 512 * 1024:
                continue
            rel = str(f.relative_to(root))
            snap["files"][rel] = f.read_text(encoding="utf-8", errors="replace")
            count += 1
        except Exception:
            continue
    path = _ckpt_dir(workdir) / f"{name}.json"
    path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    return f"Checkpoint '{name}' created ({count} files)."


def restore(workdir: str, name: str) -> str:
    path = _ckpt_dir(workdir) / f"{name}.json"
    if not path.exists():
        return f"Checkpoint not found: {name}"
    snap = json.loads(path.read_text(encoding="utf-8"))
    root = Path(workdir).resolve()
    restored = 0
    for rel, content in snap["files"].items():
        fp = root / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        restored += 1
    return f"Restored checkpoint '{name}' ({restored} files)."


def list_all(workdir: str) -> str:
    items = sorted(_ckpt_dir(workdir).glob("*.json"))
    if not items:
        return "No checkpoints."
    out = ["Checkpoints:"]
    for p in items:
        try:
            snap = json.loads(p.read_text(encoding="utf-8"))
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(snap.get("created", 0)))
            out.append(f"  {snap['name']}  ({len(snap['files'])} files, {when})")
        except Exception:
            continue
    return "\n".join(out)
