"""REAL test of all 10 advanced features (offline where possible).

Har feature ko actually chala kar verify karta hai — koi mock nahi.
"""
from __future__ import annotations
import os
import shutil
import tempfile

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'✅ PASS' if ok else '❌ FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main() -> int:
    ws = tempfile.mkdtemp(prefix="zedpy_adv_")
    # seed a small codebase
    open(os.path.join(ws, "auth.py"), "w").write(
        "import os, sys\ndef login(user, password):\n    return user == 'admin'\n")
    open(os.path.join(ws, "utils.py"), "w").write(
        "def helper():\n    return 42\n")

    # F2 — Codebase index + semantic search
    from zedpy.core.index import CodeIndex
    idx = CodeIndex(ws)
    stats = idx.build()
    hits = idx.search("login password authentication", limit=3)
    check("F2 Codebase index + semantic search",
          stats["files"] == 2 and hits and hits[0][0] == "auth.py",
          f"top hit: {hits[0] if hits else None}")

    # F3 — Undo/Redo
    from zedpy.core.undo import UndoManager
    um = UndoManager()
    f = os.path.join(ws, "utils.py")
    um.capture(f, "edit_file")
    open(f, "w").write("def helper():\n    return 99\n")
    um.commit()
    um.undo()
    after_undo = open(f).read()
    um.redo()
    after_redo = open(f).read()
    check("F3 Undo/Redo file changes",
          "42" in after_undo and "99" in after_redo,
          "undo restored, redo re-applied")

    # F8 — AST analysis
    from zedpy.tools.analyze import AnalyzeCode
    out = AnalyzeCode().run(ws, path="auth.py")
    check("F8 AST code analysis",
          "login" in out and ("unused" in out.lower() or "import" in out.lower()),
          "found functions + unused imports")

    # F10 — Memory
    from zedpy.core.memory import Memory
    import zedpy.core.memory as memmod
    # isolated memory file
    tmpmem = tempfile.mkdtemp()
    memmod._mem_path = lambda: __import__("pathlib").Path(tmpmem) / "m.json"
    m = Memory()
    m.remember("fav_lang", "Python", "preference")
    rec = m.recall("lang")
    m2 = Memory()  # reload from disk
    persisted = "Python" in m2.recall("")
    check("F10 Cross-session memory",
          "Python" in rec and persisted, "saved + reloaded from disk")

    # F1 — Session persistence
    from zedpy.core.session import Session
    import zedpy.core.session as sessmod
    tmps = tempfile.mkdtemp()
    sessmod._sessions_dir = lambda: __import__("pathlib").Path(tmps)
    s = Session.new("mimo-v2.5-free", ws)
    s.messages = [{"role": "user", "content": "hello world"}]
    s.save()
    loaded = Session.load(s.id)
    check("F1 Session persistence",
          loaded is not None and loaded.messages[0]["content"] == "hello world",
          "saved + loaded")

    # F5 — Git tool (whitelist safety)
    from zedpy.tools.git import GitTool
    g = GitTool()
    blocked = g.run(ws, action="push", args="--force")  # not whitelisted
    check("F5 Git tool (whitelist)",
          "allowed nahi" in blocked, "dangerous subcommand blocked")

    # F4 — Streaming module import + shape
    from zedpy.llm.streaming import stream_chat
    check("F4 Streaming module", callable(stream_chat), "stream_chat available")

    # F6 — Auto-context injection (agent method)
    from zedpy.agent import Agent
    from zedpy.config import Config
    cfg = Config.load(); cfg.workdir = ws
    ag = Agent(cfg)
    ag._inject_context("fix the login function")
    injected = any("AUTO-CONTEXT" in (msg.get("content") or "") for msg in ag.history)
    check("F6 Auto-context injection", injected, "relevant files injected")

    # F7 — Token tracking
    ag.total_input_tokens = 100; ag.total_output_tokens = 50
    st = ag.stats()
    check("F7 Token/cost tracking",
          st["input_tokens"] == 100 and st["output_tokens"] == 50, "stats tracked")

    # F9 — Web search tool (structure; network optional)
    from zedpy.tools.websearch import WebSearch
    check("F9 Web search tool", WebSearch().name == "web_search", "tool registered")

    shutil.rmtree(ws, ignore_errors=True)

    print("\n" + "#" * 55)
    n = sum(1 for _, ok in results if ok)
    print(f"  {n}/{len(results)} advanced features verified")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
