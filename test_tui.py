"""REAL test of the BITTU TUI: slash commands + agent file edit through the UI.

Ye Textual ki headless pilot use karke UI ko drive karta hai, real LLM ke saath.
Verify karta hai:
  1. Startup UI render hota hai (constellation + BITTU + prompt).
  2. Slash command (/mode) kaam karta hai.
  3. Agent ko UI se prompt do -> file edit ho jaati hai (disk verify).
"""
from __future__ import annotations
import asyncio
import os
import shutil
import tempfile

from zedpy.config import Config
from zedpy.tui.app import BittuApp


async def _run() -> int:
    ws = tempfile.mkdtemp(prefix="bittu_tui_")
    with open(os.path.join(ws, "app.py"), "w") as f:
        f.write("VERSION = '0.0.1'  # bump me\n")

    cfg = Config.load()
    cfg.workdir = ws
    cfg.auto_approve = True
    app = BittuApp(cfg)

    passed = []
    try:
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.pause()

            # TEST 1: startup rendered with brand.
            logo = app.query_one("#logo")
            ok1 = "BITTU" in logo.render().plain
            passed.append(("1. Startup UI (BITTU logo)", ok1))

            # TEST 2: slash command /mode plan.
            app.query_one("#prompt").value = "/mode build"
            await pilot.press("enter")
            await pilot.pause()
            ok2 = app._mode_name() == "Build"
            passed.append(("2. Slash command /mode", ok2))

            # TEST 3: agent edits a file via the UI.
            app.query_one("#prompt").value = (
                "Edit app.py: change VERSION from '0.0.1' to '1.0.0' using edit_file."
            )
            await pilot.press("enter")
            # agent worker is threaded — wait for it to finish.
            for _ in range(60):
                if not app.busy:
                    break
                await asyncio.sleep(1)
            await pilot.pause()
            content = open(os.path.join(ws, "app.py")).read()
            ok3 = "1.0.0" in content and "0.0.1" not in content
            passed.append(("3. Agent edits file via TUI (disk)", ok3))
    finally:
        shutil.rmtree(ws, ignore_errors=True)

    print("\n" + "#" * 55)
    for name, ok in passed:
        print(f"  {'✅ PASS' if ok else '❌ FAIL'}  {name}")
    n = sum(1 for _, ok in passed if ok)
    print(f"\n  {n}/{len(passed)} passed")
    return 0 if n == len(passed) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
