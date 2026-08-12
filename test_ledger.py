"""REAL offline test for the Dream Mode persistent ledger + double-verify.

No LLM / API key needed — sets PYTEST_CURRENT_TEST so the swarm decomposer
no-ops and the ledger falls back to its deterministic heuristic. Verifies the
bounded, resumable engine's new backbone:
  - ledger create/load/resume + atomic save
  - milestone status math (pending_count / is_complete)
  - verify-pass counter round-trips through disk
  - ledger_update tool
  - agent double-verify plumbing (_parse_verification / _dream_double_verify)
  - the duplicate-return bug in _dream_completion_check stays fixed
"""
from __future__ import annotations

import inspect
import os
import tempfile

# Force offline: swarm.decompose_task + run_swarm skip themselves under this.
os.environ.setdefault("PYTEST_CURRENT_TEST", "test_ledger")

from zedpy.agent import Agent
from zedpy.config import Config
from zedpy.core import ledger
from zedpy.tools import REGISTRY

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main() -> int:
    wd = tempfile.mkdtemp(prefix="zedpy_ledger_")

    # 1. Create / load round-trip.
    d = ledger.create(wd, "add logging", ["step one", "step two"])
    loaded = ledger.load(wd)
    check("create + load round-trip",
          loaded is not None and loaded["goal"] == "add logging"
          and len(loaded["milestones"]) == 2)
    check("load returns None when absent",
          ledger.load(tempfile.mkdtemp(prefix="empty_")) is None)

    # 2. resume_or_create: same goal resumes, different goal rebuilds.
    same = ledger.resume_or_create(wd, "add logging", None)
    check("resume: same goal keeps milestone ids",
          [m["id"] for m in same["milestones"]] == ["m1", "m2"])
    ledger.mark_done(wd, "m1")
    same2 = ledger.resume_or_create(wd, "add logging", None)
    check("resume: keeps done status across resume",
          any(m["id"] == "m1" and m["status"] == "done"
              for m in same2["milestones"]))
    diff = ledger.resume_or_create(wd, "a totally different goal", None)
    check("resume: different goal rebuilds fresh",
          diff["goal"] == "a totally different goal"
          and ledger.pending_count(diff) == len(diff["milestones"]))

    # 3. Heuristic decomposition: small vs large goal.
    wd_small = tempfile.mkdtemp(prefix="small_")
    s = ledger.resume_or_create(wd_small, "rename a variable in m.py", None)
    check("heuristic: small goal -> few milestones", 1 <= len(s["milestones"]) <= 2)
    wd_big = tempfile.mkdtemp(prefix="big_")
    b = ledger.resume_or_create(wd_big, "generate 40000 files for the platform", None)
    check("heuristic: 40000-file goal -> multiple coarse milestones",
          len(b["milestones"]) >= 4)

    # 4. Completion math.
    wd_c = tempfile.mkdtemp(prefix="complete_")
    ledger.create(wd_c, "g", ["a", "b"])
    check("is_complete False while pending", not ledger.is_complete(ledger.load(wd_c)))
    ledger.mark_done(wd_c, "m1")
    check("pending_count decrements", ledger.pending_count(ledger.load(wd_c)) == 1)
    ledger.mark_done(wd_c, "m2")
    check("is_complete True when all done", ledger.is_complete(ledger.load(wd_c)))

    # 5. verify_passes counter survives disk round-trip.
    ledger.create(wd_c, "g2", ["x"])
    check("bump_verify_passes 0->1", ledger.bump_verify_passes(wd_c) == 1)
    check("bump_verify_passes 1->2", ledger.bump_verify_passes(wd_c) == 2)
    ledger.reset_verify_passes(wd_c)
    check("reset_verify_passes -> 0", ledger.load(wd_c)["verify_passes"] == 0)

    # 6. ledger_update tool.
    tool = REGISTRY["ledger_update"]
    ledger.create(wd_c, "g3", ["one", "two"])
    listed = tool.run(wd_c, action="list")
    check("tool list shows pending", "one" in listed and "two" in listed)
    check("tool done marks milestone", "done" in tool.run(wd_c, action="done", item_id="m1").lower())
    check("tool add appends", "Added" in tool.run(wd_c, action="add", description="three"))
    check("tool rejects bad action", tool.run(wd_c, action="bogus").startswith("Error"))

    # 7. Agent double-verify plumbing (offline, no LLM).
    cfg = Config.load(); cfg.workdir = wd_c; cfg.effort = "dream"
    ag = Agent(cfg)
    clean = ag._parse_verification("### Fake Code Check\nFake/stub findings: 0\nall good")
    check("_parse_verification: clean report -> no problems", clean == [])
    dirty = ag._parse_verification("### Fake Code Check\nFake/stub findings: 3\n")
    check("_parse_verification: 3 findings -> flagged", any("fake" in p for p in dirty))
    synt = ag._parse_verification("boom SyntaxError: invalid syntax")
    check("_parse_verification: SyntaxError flagged", any("syntax" in p for p in synt))
    # double-verify must not raise offline (verification_plane uses local analyzers).
    try:
        both_ok, _ = ag._dream_double_verify()
        ran = True
    except Exception as e:
        ran = False
        print("   double-verify raised:", e)
    check("_dream_double_verify runs offline without raising", ran)

    # 8. Guard: the duplicate trailing return in _dream_completion_check is gone.
    src = inspect.getsource(Agent._dream_completion_check)
    check("no duplicate 'goal not verified yet' return",
          src.count('or "goal not verified yet"') == 1)

    import shutil
    for p in (wd, wd_small, wd_big, wd_c):
        shutil.rmtree(p, ignore_errors=True)

    print()
    n = sum(1 for _, ok in results if ok)
    print(f"  {n}/{len(results)} ledger / double-verify checks passed")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
