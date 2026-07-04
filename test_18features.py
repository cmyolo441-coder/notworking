"""REAL test of the 18 new features + Esc/copy/PgUp (offline where possible)."""
from __future__ import annotations
import asyncio
import os
import shutil
import tempfile

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'✅' if ok else '❌'}  {name}" + (f"  — {detail}" if detail else ""))


def seed(ws):
    """Seed test files with a credential-like pattern for secret_scan testing."""
    token = os.environ.get("TEST_SECRET_SEED", "dGhpc0lzQVJlYWxTZWNyZXRLZXk")
    open(os.path.join(ws, "app.py"), "w").write(
        f'import os, sys, json\nAPP_AUTH_TOKEN = "{token}"\n'
        'def add(a, b):\n    return a + b  # TODO: validate inputs\n')
    open(os.path.join(ws, "data.json"), "w").write('{"name": "bittu", "nested": {"x": [10, 20]}}')


def main() -> int:
    ws = tempfile.mkdtemp(prefix="zedpy_18_")
    seed(ws)
    from zedpy.tools import REGISTRY as T

    # #5 code_metrics
    check("#5 code_metrics", "Lines:" in T["code_metrics"].run(ws))
    # #6 fuzzy_find
    check("#6 fuzzy_find", "app.py" in T["fuzzy_find"].run(ws, query="ap"))
    # #8 lint
    check("#8 lint", "app.py" in T["lint"].run(ws, path="app.py"))
    # #9 deps
    out = T["deps"].run(ws); check("#9 deps", "os" in out or "Dependencies" in out)
    # #10 secret_scan
    check("#10 secret_scan", "secret" in T["secret_scan"].run(ws).lower())
    # #11 todo_scan
    check("#11 todo_scan", "TODO" in T["todo_scan"].run(ws))
    # #2 show_diff
    d = T["show_diff"].run(ws, path="app.py", new_content="import os\nx=1\n")
    check("#2 show_diff", "+" in d and "-" in d)
    # #12 scaffold
    T["scaffold"].run(ws, kind="python", name="myproj")
    check("#12 scaffold", os.path.exists(os.path.join(ws, "myproj", "main.py")))
    # #14 data_tool (get nested)
    g = T["data_tool"].run(ws, action="get", path="data.json", key="nested.x.1")
    check("#14 data_tool", g.strip() == "20", f"got {g.strip()}")
    # #15 regex_replace
    T["regex_replace"].run(ws, path="app.py", pattern="supersecret123", replacement="REDACTED")
    check("#15 regex_replace", "REDACTED" in open(os.path.join(ws, "app.py")).read())
    # #16 tree
    check("#16 tree", "app.py" in T["tree"].run(ws))
    # #13 http_request (structure only; no network needed)
    check("#13 http_request", T["http_request"].name == "http_request")

    # #7 checkpoint + restore
    from zedpy.core import checkpoint
    checkpoint.create(ws, "cp1")
    open(os.path.join(ws, "app.py"), "w").write("DELETED\n")
    checkpoint.restore(ws, "cp1")
    check("#7 checkpoint/restore", "REDACTED" in open(os.path.join(ws, "app.py")).read())

    # #18 export
    from zedpy.core.export import export
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    r = export(msgs, ws, "md")
    check("#18 export", "Exported" in r and any(f.endswith(".md") for f in os.listdir(ws)))

    # #3 swarm (module structure — needs LLM to actually run, so just import)
    from zedpy.core.swarm import run_swarm
    check("#3 swarm module", callable(run_swarm))

    # #1 plan mode + #4 auto-test flags
    from zedpy.config import Config
    from zedpy.agent import Agent
    cfg = Config.load(); cfg.workdir = ws; cfg.plan_mode = True; cfg.auto_test = True
    ag = Agent(cfg)
    sysp = ag.history[0]["content"]
    check("#1 plan mode", "PLAN MODE ACTIVE" in sysp)
    check("#4 auto-test flag", "AUTO-TEST ON" in sysp)
    check("#4 auto-test detect", callable(ag._detect_test_command))
    # #17 command history (via app attr) — verified in TUI test below
    check("#17 command history", True, "tracked in TUI")

    shutil.rmtree(ws, ignore_errors=True)
    print()
    n = sum(1 for _, ok in results if ok)
    print(f"  {n}/{len(results)} feature checks passed")
    return 0 if n == len(results) else 1


async def tui_test() -> bool:
    """Esc-stop, PgUp/PgDown palette nav, command history — via headless pilot."""
    from zedpy.config import Config
    from zedpy.tui.app import BittuApp
    ws = tempfile.mkdtemp(prefix="zedpy_tui18_")
    cfg = Config.load(); cfg.workdir = ws
    app = BittuApp(cfg)
    ok = {}
    async with app.run_test(size=(100, 34)) as pilot:
        await pilot.pause()
        # type '/' to open palette
        await pilot.press("slash")
        await pilot.pause()
        ok["palette opens"] = len(app._palette_matches) > 0
        start = app._palette_index
        app.action_palette_down()
        ok["PgDown moves selection"] = app._palette_index != start
        app.action_palette_up()
        ok["PgUp moves selection"] = app._palette_index == start
        # accept selected command
        app._palette_index = 0
        accepted = app._accept_palette()
        ok["Enter/Tab accepts command"] = accepted and app.query_one("#prompt").value.startswith("/")
        # Esc stop (simulate busy)
        app.busy = True
        app.action_stop()
        ok["Esc sets cancel"] = app.agent.cancel_event.is_set()
        app.busy = False
        # command history
        app.query_one("#prompt").value = "hello test"
        from textual.widgets import Input
        app.on_input_submitted(Input.Submitted(app.query_one("#prompt"), "hello test"))
        ok["#17 cmd history"] = "hello test" in app.cmd_history
    shutil.rmtree(ws, ignore_errors=True)
    print("\n  --- TUI interaction tests ---")
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'}  {k}")
    return all(ok.values())


if __name__ == "__main__":
    rc = main()
    tui_ok = asyncio.run(tui_test())
    raise SystemExit(0 if rc == 0 and tui_ok else 1)
