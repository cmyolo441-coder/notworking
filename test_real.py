"""REAL end-to-end test for zedpy.

Ye asli LLM (mimo-v2.5-free) ke saath agent ko chalata hai aur VERIFY karta hai:
  1. Agent file READ kar sakta hai?
  2. Agent file EDIT kar sakta hai (aur disk par sach me badla)?
  3. Agent SHELL command chala sakta hai?
  4. Agent naya file WRITE kar sakta hai?

Chalao:  cd zedpy && python3 test_real.py
Ye ek temp workdir banata hai taaki tumhari real files safe rahein.
Auto-approve ON hai (test non-interactive hai).
"""
from __future__ import annotations
import os
import shutil
import sys
import tempfile

# zedpy import ho sake.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zedpy.config import Config
from zedpy.agent import Agent

PASS, FAIL = "✅ PASS", "❌ FAIL"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"\n{'='*60}\n{PASS if ok else FAIL}  {name}\n{'='*60}")
    if detail:
        print(f"   {detail}")


def main() -> int:
    ws = tempfile.mkdtemp(prefix="zedpy_test_")
    print(f"[setup] temp workdir: {ws}")

    # Seed files.
    with open(os.path.join(ws, "notes.txt"), "w") as f:
        f.write("hello world\nthis is line two\nMAGIC_TOKEN_123\n")
    with open(os.path.join(ws, "calc.py"), "w") as f:
        f.write("def add(a, b):\n    return a - b  # BUG: should be +\n")

    cfg = Config.load()
    cfg.workdir = ws
    cfg.auto_approve = True  # non-interactive test
    agent = Agent(cfg)

    try:
        # --- TEST 1: READ ------------------------------------------------
        agent.run("Read the file notes.txt and tell me exactly what secret token it contains.")
        # Agent ki reply me token hona chahiye -> matlab usne padha.
        last = agent.history[-1]["content"]
        check("1. READ file", "MAGIC_TOKEN_123" in last,
              f"agent reply me token mila: {'MAGIC_TOKEN_123' in last}")

        # --- TEST 2: EDIT ------------------------------------------------
        agent.run("The file calc.py has a bug: add() subtracts instead of adds. "
                  "Fix it using edit_file so it returns a + b.")
        fixed = open(os.path.join(ws, "calc.py")).read()
        ok2 = "a + b" in fixed and "a - b" not in fixed
        check("2. EDIT file (disk verify)", ok2,
              f"calc.py ab: {fixed.strip()!r}")

        # --- TEST 3: SHELL -----------------------------------------------
        agent.run("Run the shell command 'echo ZEDPY_SHELL_OK' and tell me the output.")
        # tool result history me shell output hona chahiye.
        shell_ran = any(
            m.get("role") == "tool" and "ZEDPY_SHELL_OK" in (m.get("content") or "")
            for m in agent.history
        )
        check("3. SHELL command", shell_ran,
              f"shell output history me mila: {shell_ran}")

        # --- TEST 4: WRITE new file --------------------------------------
        agent.run("Create a new file greeting.py that prints 'Hi from zedpy'. "
                  "Then run it with python3 and confirm the output.")
        created = os.path.exists(os.path.join(ws, "greeting.py"))
        ran_ok = any(
            m.get("role") == "tool" and "Hi from zedpy" in (m.get("content") or "")
            for m in agent.history
        )
        check("4. WRITE + RUN new file", created and ran_ok,
              f"file bana: {created}, run output mila: {ran_ok}")

    finally:
        shutil.rmtree(ws, ignore_errors=True)
        print(f"\n[cleanup] removed {ws}")

    # --- Summary --------------------------------------------------------
    print(f"\n{'#'*60}\n# RESULTS\n{'#'*60}")
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, _ in results:
        print(f"  {PASS if ok else FAIL}  {name}")
    print(f"\n  {passed}/{len(results)} tests passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
