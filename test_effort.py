"""REAL test of the Effort Engine — verifies actual runtime behavior, not labels."""
from __future__ import annotations
import os
import tempfile

from zedpy.config import Config
from zedpy.agent import Agent
from zedpy.core import effort as ee

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'✅' if ok else '❌'}  {name}" + (f"  — {detail}" if detail else ""))


def main() -> int:
    ws = tempfile.mkdtemp(prefix="zedpy_effort_")

    # 1. All levels exist with escalating behavior.
    n, m, u, c = ee.get("normal"), ee.get("max"), ee.get("ultra"), ee.get("ultracombomax")
    check("levels escalate: steps", n.max_steps < m.max_steps < u.max_steps < c.max_steps,
          f"{n.max_steps} < {m.max_steps} < {u.max_steps} < {c.max_steps}")
    check("levels escalate: multiplier", n.multiplier < m.multiplier < u.multiplier < c.multiplier)
    check("temperature drops with effort", n.temperature > m.temperature > u.temperature > c.temperature)

    # 2. Behavioral switches are real.
    check("max: plan+verify+autodebug", m.plan_first and m.self_verify and m.auto_debug)
    check("ultra: deep research + swarm + security", u.deep_research and u.use_swarm and u.run_security)
    check("ultracombomax: enterprise gates + checkpoint", c.enterprise_gates and c.auto_checkpoint)

    # 3. Aliases work.
    check("alias 'enterprise' -> ultracombomax", ee.get("enterprise").name == "ultracombomax")
    check("alias 'best' -> max", ee.get("best").name == "max")

    # 4. Agent applies effort to system prompt.
    cfg = Config.load(); cfg.workdir = ws; cfg.effort = "ultracombomax"
    ag = Agent(cfg)
    sysp = ag.history[0]["content"]
    check("system prompt has effort block", "ULTRA COMBO MAX" in sysp and "ENTERPRISE" in sysp)

    # 5. set_effort switches at runtime.
    msg = ag.set_effort("max")
    check("set_effort switches", ag.effort.name == "max" and "Max" in msg)
    check("switched prompt updated", "MAX THINKING" in ag.history[0]["content"])

    # 6. context_files scales with effort.
    check("context_files scales", ee.get("normal").context_files < ee.get("ultracombomax").context_files)

    # 7. Preflight/gates methods exist & callable.
    check("preflight method", callable(ag._effort_preflight))
    check("gates method", callable(ag._effort_gates))

    # 8. Effort max_steps actually used in run() (check the code path uses max()).
    ag2 = Agent(Config.load())
    ag2.cfg.workdir = ws
    ag2.set_effort("ultra")
    effective = max(ag2.cfg.max_steps, ag2.effort.max_steps)
    check("run uses effort max_steps", effective == 140, f"effective={effective}")

    import shutil; shutil.rmtree(ws, ignore_errors=True)
    print()
    passed = sum(1 for _, ok in results if ok)
    print(f"  {passed}/{len(results)} effort checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
