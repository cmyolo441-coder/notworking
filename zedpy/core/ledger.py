"""Persistent Dream-Mode task ledger — the never-stop engine's source of truth.

Dream Mode ka asli problem: model beech me tool-calls band kar deta tha aur loop
"done" maan leta tha. Ledger isko fix karta hai — goal ko concrete milestones me
tod kar `.zedpy/dream_ledger.json` me save karta hai. Loop tab tak nahi rukta jab
tak har pending milestone `done` na ho AND double-verify pass na ho.

Crash/restart safe: 40K-file job beech me rukey to same goal par `resume_or_create`
purana ledger wapas load kar deta hai (goal_hash match) — kaam wahi se continue.

Design notes:
  - save() atomic hai (temp file + os.replace) — crash mid-write par corruption nahi.
  - load() kabhi raise nahi karta — missing/corrupt par None, caller rebuild kar leta.
  - Population online (swarm.decompose_task via LLM) ya offline (deterministic
    heuristic) dono se hoti hai, isliye pytest/CI me bhi bina API key ke chalta hai.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

_VERSION = 1


# ---------------------------------------------------------------------------
# Disk layout (mirrors core/checkpoint.py conventions — writes under .zedpy/).
# ---------------------------------------------------------------------------

def _ledger_path(workdir: str) -> Path:
    d = Path(workdir) / ".zedpy"
    d.mkdir(parents=True, exist_ok=True)
    return d / "dream_ledger.json"


def _goal_hash(goal: str) -> str:
    return hashlib.sha1((goal or "").strip().encode("utf-8")).hexdigest()[:16]


def load(workdir: str) -> dict | None:
    """Load the ledger. Returns None on missing/corrupt — never raises.

    A crash mid-write can only leave the *temp* file half-written; the real
    file is swapped atomically by save(), so a present file is always valid
    JSON. Corruption still returns None so the caller rebuilds cleanly.
    """
    path = _ledger_path(workdir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or "milestones" not in data:
        return None
    return data


def save(workdir: str, data: dict) -> None:
    """Atomically persist the ledger (temp-write then os.replace)."""
    data["updated"] = time.time()
    path = _ledger_path(workdir)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.replace(tmp, path)  # atomic on POSIX + Windows


# ---------------------------------------------------------------------------
# Construction.
# ---------------------------------------------------------------------------

def _milestone(mid: str, description: str, target: str = "") -> dict:
    now = time.time()
    return {
        "id": mid,
        "description": description,
        "target": target,
        "status": "pending",
        "evidence": "",
        "created": now,
        "updated": now,
    }


def create(workdir: str, goal: str, milestones: list[str]) -> dict:
    """Build a fresh ledger from a list of milestone descriptions and save it."""
    now = time.time()
    items = [_milestone(f"m{i}", desc) for i, desc in enumerate(milestones, 1)]
    data = {
        "version": _VERSION,
        "goal": goal,
        "goal_hash": _goal_hash(goal),
        "created": now,
        "updated": now,
        "verify_passes": 0,
        "milestones": items,
    }
    save(workdir, data)
    return data


def resume_or_create(workdir: str, goal: str, cfg=None) -> dict:
    """Main entry: resume an existing ledger for the same goal, else build one.

    This is how a crashed 40K-file job continues — same goal → same goal_hash →
    the on-disk milestones (with their done/pending status) come straight back.
    """
    existing = load(workdir)
    if existing is not None and existing.get("goal_hash") == _goal_hash(goal):
        return existing
    milestones = _decompose(goal, cfg)
    return create(workdir, goal, milestones)


# ---------------------------------------------------------------------------
# Goal decomposition — online (LLM swarm) with a deterministic offline fallback.
# ---------------------------------------------------------------------------

_LARGE_WORDS = ("entire", "all files", "every file", "whole codebase",
                "codebase", "everything", "every module")


def _looks_large(goal: str) -> bool:
    """True if the goal implies bulk/multi-file scale (e.g. '40000 files')."""
    g = (goal or "").lower()
    # A number >= 100 sitting near the word "file(s)".
    for m in re.finditer(r"(\d[\d,]{2,})\s*(?:k\b|thousand|files?|modules?)", g):
        digits = m.group(1).replace(",", "")
        try:
            if int(digits) >= 100:
                return True
        except ValueError:
            pass
    # "40k files" style.
    if re.search(r"\b\d+\s*k\b.*file", g):
        return True
    return any(w in g for w in _LARGE_WORDS)


def _heuristic_milestones(goal: str) -> list[str]:
    """Deterministic decomposition used offline / when the LLM is unavailable."""
    short = goal.strip()
    if len(short) > 90:
        short = short[:90] + "…"
    if _looks_large(goal):
        # Coarse *phase* milestones — deliberately NOT one row per file. The
        # fake-scan + test gates track file-level reality; these track phases.
        return [
            f"Scaffold project structure for: {short}",
            "Implement core modules with REAL working code (no stubs)",
            "Implement all remaining files up to the target count",
            "Write and run tests until they pass",
            "Eliminate every fake/stub/simulated finding (fake_scan == 0)",
        ]
    # Small, focused goal.
    return [f"Implement: {short}", "Verify tests pass and no fake code remains"]


def _decompose(goal: str, cfg) -> list[str]:
    """Return milestone descriptions for a goal.

    Tries the LLM swarm decomposer (skips itself in CI/pytest and falls back to
    [goal]); if that yields nothing useful, uses the offline heuristic. Any
    exception → heuristic. Always returns >= 1 milestone.
    """
    if cfg is not None:
        try:
            from .swarm import decompose_task
            tasks = decompose_task(goal, cfg)
            # decompose_task returns [goal] when offline/failed — treat that as
            # "no real decomposition" and fall through to the heuristic.
            cleaned = [t.strip() for t in tasks if t and t.strip()]
            if len(cleaned) >= 2:
                return cleaned[:12]
        except Exception:
            pass
    return _heuristic_milestones(goal)


# ---------------------------------------------------------------------------
# Mutation.
# ---------------------------------------------------------------------------

def add_milestone(workdir: str, description: str, target: str = "") -> str:
    data = load(workdir)
    if data is None:
        return "Error: no ledger to add to."
    existing_ids = {m["id"] for m in data["milestones"]}
    n = len(data["milestones"]) + 1
    while f"m{n}" in existing_ids:
        n += 1
    data["milestones"].append(_milestone(f"m{n}", description, target))
    save(workdir, data)
    return f"Added milestone m{n}: {description}"


def update_item(workdir: str, item_id: str, status: str,
                evidence: str = "") -> str:
    data = load(workdir)
    if data is None:
        return "Error: no ledger."
    if status not in ("pending", "in_progress", "done"):
        return f"Error: invalid status {status!r}."
    for m in data["milestones"]:
        if m["id"] == item_id:
            m["status"] = status
            if evidence:
                m["evidence"] = evidence
            m["updated"] = time.time()
            save(workdir, data)
            return f"Milestone {item_id} -> {status}."
    return f"Error: milestone {item_id!r} not found."


def mark_done(workdir: str, item_id: str, evidence: str = "") -> str:
    return update_item(workdir, item_id, "done", evidence)


# ---------------------------------------------------------------------------
# Queries.
# ---------------------------------------------------------------------------

def pending_count(data: dict | None) -> int:
    if not data:
        return 0
    return sum(1 for m in data.get("milestones", []) if m.get("status") != "done")


def is_complete(data: dict | None) -> bool:
    """True only if there are milestones AND none are pending."""
    if not data:
        return False
    milestones = data.get("milestones", [])
    return bool(milestones) and pending_count(data) == 0


def pending_summary(data: dict | None, limit: int = 8) -> str:
    if not data:
        return "(no ledger)"
    milestones = data.get("milestones", [])
    done = sum(1 for m in milestones if m.get("status") == "done")
    lines = [f"Ledger: {done}/{len(milestones)} milestones done "
             f"(goal: {str(data.get('goal', ''))[:70]})"]
    shown = 0
    for m in milestones:
        if m.get("status") == "done":
            continue
        mark = "→" if m.get("status") == "in_progress" else "·"
        lines.append(f"  {mark} [{m['id']}] {m['description']}")
        shown += 1
        if shown >= limit:
            remaining = pending_count(data) - shown
            if remaining > 0:
                lines.append(f"  … +{remaining} more pending")
            break
    if shown == 0:
        lines.append("  ✓ all milestones done")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Double-verify pass counter (consecutive-clean; reset on any new edit/fail).
# ---------------------------------------------------------------------------

def bump_verify_passes(workdir: str) -> int:
    data = load(workdir)
    if data is None:
        return 0
    data["verify_passes"] = int(data.get("verify_passes", 0)) + 1
    save(workdir, data)
    return data["verify_passes"]


def reset_verify_passes(workdir: str) -> None:
    data = load(workdir)
    if data is None:
        return
    if data.get("verify_passes"):
        data["verify_passes"] = 0
        save(workdir, data)
