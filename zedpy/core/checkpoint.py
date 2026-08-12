"""Named project checkpoints with validated manifests and atomic restore."""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

from ..tools.base import MAX_TEXT_READ_BYTES, walk_files, safe_path

_TEXT_EXT = {
    ".py", ".js", ".ts", ".go", ".md", ".txt", ".json", ".yaml", ".yml",
    ".toml", ".html", ".css", ".sh", ".rs", ".c", ".cpp", ".jsx", ".tsx",
}
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


def _ckpt_dir(workdir: str) -> Path:
    root = Path(workdir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"working directory directory nahi hai: {workdir}")
    d = root / ".zedpy" / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(name: str) -> str:
    value = (name or "").strip()
    if not value:
        value = time.strftime("ckpt-%Y%m%d-%H%M%S")
    if not _NAME_RE.fullmatch(value):
        raise ValueError("checkpoint name me sirf letters, numbers, dot, dash aur underscore allowed hain")
    return value


def _atomic_write(path: Path, data: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def create(workdir: str, name: str = "") -> str:
    root = Path(workdir).expanduser().resolve(strict=True)
    checkpoint_name = _safe_name(name)
    snap = {"version": 1, "name": checkpoint_name, "created": time.time(), "files": {}}
    count = 0
    for file_path in walk_files(root):
        if file_path.suffix.lower() not in _TEXT_EXT:
            continue
        try:
            size = file_path.stat().st_size
            if size > 512 * 1024:
                continue
            rel = file_path.relative_to(root).as_posix()
            snap["files"][rel] = file_path.read_text(encoding="utf-8", errors="replace")
            count += 1
        except (OSError, UnicodeError):
            continue
    checkpoint_path = _ckpt_dir(workdir) / f"{checkpoint_name}.json"
    payload = json.dumps(snap, ensure_ascii=False, indent=2)
    _atomic_write(checkpoint_path, payload)
    return f"Checkpoint '{checkpoint_name}' created ({count} files)."


def _load_snapshot(workdir: str, name: str) -> dict:
    checkpoint_name = _safe_name(name)
    path = _ckpt_dir(workdir) / f"{checkpoint_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"checkpoint corrupt hai: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError("checkpoint manifest invalid hai")
    if data.get("version", 1) != 1:
        raise ValueError(f"unsupported checkpoint version: {data.get('version')}")
    return data


def restore(workdir: str, name: str) -> str:
    try:
        snap = _load_snapshot(workdir, name)
        root = Path(workdir).expanduser().resolve(strict=True)
        restored = 0
        skipped = 0
        for rel, content in snap["files"].items():
            if not isinstance(rel, str) or not isinstance(content, str):
                skipped += 1
                continue
            try:
                target = safe_path(workdir, rel)
            except (OSError, ValueError):
                skipped += 1
                continue
            if len(content.encode("utf-8")) > MAX_TEXT_READ_BYTES:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(target, content)
            restored += 1
        suffix = f", {skipped} invalid entries skipped" if skipped else ""
        return f"Restored checkpoint '{snap.get('name', name)}' ({restored} files{suffix})."
    except (OSError, ValueError) as exc:
        return f"Error: restore failed: {exc}"


def list_all(workdir: str) -> str:
    try:
        items = sorted(_ckpt_dir(workdir).glob("*.json"))
    except (OSError, ValueError) as exc:
        return f"Error: checkpoint directory unavailable: {exc}"
    if not items:
        return "No checkpoints."
    out = ["Checkpoints:"]
    for path in items:
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(snap.get("created", 0)))
            out.append(f"  {snap.get('name', path.stem)}  ({len(snap.get('files', {}))} files, {when})")
        except (OSError, json.JSONDecodeError, AttributeError):
            out.append(f"  {path.stem}  (corrupt or unreadable)")
    return "\n".join(out)
