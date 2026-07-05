"""Claude Code / Grok CLI-style slash commands.

Har command ka ek naam, ek short description, aur ek handler hota hai. Jab user
'/' se shuru karta hai to ek autocomplete dropdown dikhta hai (TUI me).
Handlers ko app object milta hai taaki wo UI/agent state badal saken.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class SlashCommand:
    name: str          # e.g. "/help"  (leading slash included)
    summary: str       # short one-line description shown in the dropdown
    handler: Callable  # fn(app, arg_str) -> str  (return text to show, or "")


# --- Handlers ---------------------------------------------------------------
# Sabhi handlers `app` (BittuApp) aur `arg` (command ke baad ka text) lete hain
# aur ek string return karte hain jo transcript me dikhega ("" = kuch mat dikhao).

def _help(app, arg: str) -> str:
    lines = ["Available commands:"]
    for c in COMMANDS:
        lines.append(f"  {c.name:<12} {c.summary}")
    return "\n".join(lines)


def _clear(app, arg: str) -> str:
    app.reset_conversation()
    return "Conversation cleared."


def _model(app, arg: str) -> str:
    from .config import MODEL_PROFILES
    arg = arg.strip()
    if not arg:
        # Show interactive model selector in TUI
        if hasattr(app, '_show_model_selector'):
            app._show_model_selector()
            return ""
        # Fallback for non-TUI mode
        cur = app.cfg.model
        profiles = ", ".join(MODEL_PROFILES.keys())
        return (f"Current model: {cur}\n"
                f"Available profiles: {profiles}\n"
                f"Usage: /model <name> (e.g. /model glm, /model kimi, /model mimo)")
    # Check if it's a named profile
    if arg.lower() in MODEL_PROFILES:
        app.cfg.apply_profile(arg.lower())
        # Rebuild agent if in TUI
        if hasattr(app, 'agent'):
            from .agent import Agent
            app.agent = Agent(app.cfg)
        app.refresh_status()
        return f"Model → {app.cfg.model} (via profile '{arg}')\nBase URL: {app.cfg.base_url}"
    # Otherwise treat as raw model name
    app.cfg.model = arg
    if hasattr(app, 'agent'):
        from .agent import Agent
        app.agent = Agent(app.cfg)
    app.refresh_status()
    return f"Model set to: {app.cfg.model}"


def _mode(app, arg: str) -> str:
    """Cycle / set the mode (Plan / Build / Chat) — Grok CLI 'tab modes'."""
    if arg.strip():
        return app.set_mode(arg.strip())
    return app.cycle_mode()


def _cwd(app, arg: str) -> str:
    if arg.strip():
        return app.change_workdir(arg.strip())
    return f"Working directory: {app.cfg.workdir}"


def _init(app, arg: str) -> str:
    """Create a BITTU.md instructions file (like Claude Code /init)."""
    return app.run_agent_task(
        "Create a BITTU.md file in the project root that documents this codebase: "
        "its purpose, structure, how to build/run/test it, and conventions. "
        "Explore the files first with list_dir and read_file."
    )


def _login(app, arg: str) -> str:
    return app.open_login()


def _setkey(app, arg: str) -> str:
    """Save API key to config file."""
    import os
    arg = arg.strip()
    if not arg:
        return (
            "Usage: /setkey <api-key>\n"
            "Or set env: export ZEDPY_API_KEY='your-key'\n"
            "Or: export OPENCODE_API_KEY='your-key'\n"
            "Or: export NVIDIA_API_KEY='nvapi-...'"
        )

    # Determine which provider based on current base_url
    base_url = app.cfg.base_url
    if "nvidia.com" in base_url:
        config_dir = os.path.expanduser("~/.config/zedpy")
    elif "cloudflare.com" in base_url:
        config_dir = os.path.expanduser("~/.config/zedpy")
    else:
        config_dir = os.path.expanduser("~/.config/zedpy")

    # Save to config file
    os.makedirs(config_dir, exist_ok=True)
    key_file = os.path.join(config_dir, "api_key")
    with open(key_file, 'w') as f:
        f.write(arg)

    # Also set in current config
    app.cfg.api_key = arg

    return f"API key saved to {key_file}\nModel: {app.cfg.model}\nProvider: {base_url}"


def _config(app, arg: str) -> str:
    return (
        f"model      : {app.cfg.model}\n"
        f"base_url   : {app.cfg.base_url}\n"
        f"workdir    : {app.cfg.workdir}\n"
        f"max_steps  : {app.cfg.max_steps}\n"
        f"auto_apply : {app.cfg.auto_approve}"
    )


def _tools(app, arg: str) -> str:
    from .tools import TOOLS
    lines = ["Registered tools:"]
    for t in TOOLS:
        gate = " (needs approval)" if t.requires_approval else ""
        lines.append(f"  {t.name:<14} {t.description[:60]}{gate}")
    return "\n".join(lines)


def _yolo(app, arg: str) -> str:
    app.cfg.auto_approve = not app.cfg.auto_approve
    app.refresh_status()
    return f"Auto-approve is now {'ON' if app.cfg.auto_approve else 'OFF'}."


def _quit(app, arg: str) -> str:
    app.exit()
    return ""


# --- Advanced feature commands ---------------------------------------------

def _undo(app, arg: str) -> str:  # F3
    from .core.undo import MANAGER
    return MANAGER.undo()


def _redo(app, arg: str) -> str:  # F3
    from .core.undo import MANAGER
    return MANAGER.redo()


def _sessions(app, arg: str) -> str:  # F1
    from .core.session import Session
    items = Session.list_all()
    if not items:
        return "No saved sessions."
    import time as _t
    lines = ["Saved sessions:"]
    for s in items[:15]:
        when = _t.strftime("%Y-%m-%d %H:%M", _t.localtime(s["updated"]))
        lines.append(f"  {s['id']}  [{s['messages']} msgs]  {when}  {s['title']}")
    lines.append("\nResume: /resume <id>  (ya /resume last)")
    return "\n".join(lines)


def _resume(app, arg: str) -> str:  # F1
    return app.resume_session(arg.strip())


def _search(app, arg: str) -> str:  # F2
    if not arg.strip():
        return "Usage: /search <query>"
    hits = app.agent.index.search(arg.strip(), limit=8)
    if not hits:
        return "No relevant files."
    return "Relevant files:\n" + "\n".join(f"  {r}  ({s})" for r, s in hits)


def _index(app, arg: str) -> str:  # F2
    stats = app.agent.index.build()
    return f"Indexed {stats['files']} files, {stats['terms']} unique terms."


def _memory(app, arg: str) -> str:  # F10
    from .core.memory import MEMORY
    return MEMORY.recall(arg.strip())


def _cost(app, arg: str) -> str:  # F7
    s = app.agent.stats()
    return (f"Tokens — input: {s['input_tokens']}  output: {s['output_tokens']}\n"
            f"Messages in context: {s['messages']}")


def _git(app, arg: str) -> str:  # F5
    action, _, rest = arg.strip().partition(" ")
    if not action:
        action = "status"
    from .tools import REGISTRY as TR
    return TR["git"].run(app.cfg.workdir, action=action, args=rest)


# --- New 18 advanced-feature commands --------------------------------------

def _plan(app, arg: str) -> str:  # #1
    app.cfg.plan_mode = not app.cfg.plan_mode
    app.agent.rebuild_system()
    return f"Plan mode {'ON — agent plans first' if app.cfg.plan_mode else 'OFF'}."


def _autotest(app, arg: str) -> str:  # #4
    app.cfg.auto_test = not app.cfg.auto_test
    app.agent.rebuild_system()
    return f"Auto-test {'ON — tests run after edits' if app.cfg.auto_test else 'OFF'}."


def _checkpoint(app, arg: str) -> str:  # #7
    from .core import checkpoint
    return checkpoint.create(app.cfg.workdir, arg.strip())


def _restore(app, arg: str) -> str:  # #7
    from .core import checkpoint
    if not arg.strip():
        return "Usage: /restore <checkpoint-name>  (see /checkpoints)"
    return checkpoint.restore(app.cfg.workdir, arg.strip())


def _checkpoints(app, arg: str) -> str:  # #7
    from .core import checkpoint
    return checkpoint.list_all(app.cfg.workdir)


def _swarm(app, arg: str) -> str:  # #3
    if not arg.strip():
        return "Usage: /swarm task1 | task2 | task3"
    subtasks = [t.strip() for t in arg.split("|") if t.strip()]
    from .core.swarm import run_swarm
    return run_swarm(app.cfg, subtasks)


def _export(app, arg: str) -> str:  # #18
    from .core.export import export
    fmt = arg.strip() or "md"
    return export(app.agent.history, app.cfg.workdir, fmt)


def _metrics(app, arg: str) -> str:  # #5
    from .tools import REGISTRY as TR
    return TR["code_metrics"].run(app.cfg.workdir, path=arg.strip() or ".")


def _secrets(app, arg: str) -> str:  # #10
    from .tools import REGISTRY as TR
    return TR["secret_scan"].run(app.cfg.workdir, path=arg.strip() or ".")


def _todos(app, arg: str) -> str:  # #11
    from .tools import REGISTRY as TR
    return TR["todo_scan"].run(app.cfg.workdir, path=arg.strip() or ".")


def _tree(app, arg: str) -> str:  # #16
    from .tools import REGISTRY as TR
    return TR["tree"].run(app.cfg.workdir, path=arg.strip() or ".")


def _history(app, arg: str) -> str:  # #17
    hist = getattr(app, "cmd_history", [])
    if not hist:
        return "(no command history)"
    return "Recent inputs:\n" + "\n".join(f"  {i+1}. {h}" for i, h in enumerate(hist[-20:]))


# --- Effort engine commands -------------------------------------------------

def _effort(app, arg: str) -> str:
    from .core import effort as ee
    if not arg.strip():
        cur = app.agent.effort
        return (f"Current effort: {cur.label} ({cur.multiplier}× · {cur.max_steps} steps)\n\n"
                + ee.summary_table()
                + "\n\nSet: /effort <name>  ·  shortcuts: /max /ultra /ultracombomax")
    msg = app.agent.set_effort(arg.strip())
    app.cfg.effort = app.agent.effort.name
    app.refresh_status()
    return msg


def _max(app, arg: str) -> str:
    r = app.agent.set_effort("max")
    app.cfg.effort = "max"
    app.refresh_status()
    return r + "  — best work, deep thinking"


def _ultra(app, arg: str) -> str:
    r = app.agent.set_effort("ultra")
    app.cfg.effort = "ultra"
    app.refresh_status()
    return r + "  — most complex work, ultra thinking"


def _ultracombomax(app, arg: str) -> str:
    r = app.agent.set_effort("ultracombomax")
    app.cfg.effort = "ultracombomax"
    app.refresh_status()
    return r + "  — full enterprise-level heavy work"


def _goal(app, arg: str) -> str:
    app.agent.set_effort("goal")
    app.cfg.effort = "goal"
    app.refresh_status()
    if arg.strip():
        # Directly launch the autonomous goal.
        app.log_user(f"/goal {arg.strip()}")
        app._run_agent_async(arg.strip())
        return ""
    return ("🎯 Goal Mode ON — fully autonomous, auto-accept. "
            "Ab apna goal type karo (ya: /goal <goal text>).")


def _dream(app, arg: str) -> str:
    app.agent.set_effort("dream")
    app.cfg.effort = "dream"
    app.refresh_status()
    if arg.strip():
        app.log_user(f"/dream {arg.strip()}")
        app._run_agent_async(arg.strip())
        return ""
    return ("🌙 DREAM MODE ON — 1000× maximum autonomy. Har tool, feature aur "
            "command orchestrate hoga, auto-accept ON, full verification + evidence. "
            "Ab apna goal type karo (ya: /dream <goal text>).")


def _dream_fast(app, arg: str) -> str:
    """Dream Mode with auto fast model selection for quick responses."""
    from .config import MODEL_PROFILES
    from .core.dream import get_dream_fast_model

    # Set dream effort
    app.agent.set_effort("dream")
    app.cfg.effort = "dream"

    # Auto-select fastest model using apply_profile
    fast_model = get_dream_fast_model()
    if fast_model in MODEL_PROFILES:
        app.cfg.apply_profile(fast_model)

    # Rebuild agent with new settings
    if hasattr(app, 'agent'):
        from .agent import Agent
        app.agent = Agent(app.cfg)

    app.refresh_status()

    if arg.strip():
        app.log_user(f"/dream-fast {arg.strip()}")
        app._run_agent_async(arg.strip())
        return ""

    return (f"🚀 DREAM MODE ULTRA PRO — Fast Model Active!\n"
            f"Model: {app.cfg.model}\n"
            f"Max Tokens: {app.cfg.max_tokens}\n"
            f"Effort: 1000× Dream Mode\n\n"
            f"14 parallel analysis engines ready:\n"
            f"  - Deep AST Analysis\n"
            f"  - Dependency Graph\n"
            f"  - Security Analysis\n"
            f"  - Performance Analysis\n"
            f"  - Code Quality Baseline\n"
            f"  - Architecture Brain\n"
            f"  - Risk Heatmap\n"
            f"  - Change Impact\n"
            f"  - Dead Code Detection\n"
            f"  - Type Hints Analysis\n"
            f"  - Code Smells\n"
            f"  - API Surface\n"
            f"  - Test Coverage\n"
            f"  - Documentation\n\n"
            f"Type your goal to start DREAM MODE ULTRA PRO!")


def _dream_ultra(app, arg: str) -> str:
    """Dream Mode ULTRA PRO with maximum analysis and verification."""
    from .config import MODEL_PROFILES
    from .core.dream import get_dream_fast_model

    # Set dream effort with maximum settings
    app.agent.set_effort("dream")
    app.cfg.effort = "dream"

    # Use best available model using apply_profile
    fast_model = get_dream_fast_model()
    if fast_model in MODEL_PROFILES:
        app.cfg.apply_profile(fast_model)

    # Enable all advanced features including auto-approve (dream mode requires it)
    app.cfg.plan_mode = False   # Dream mode handles planning internally
    app.cfg.auto_test = True
    app.cfg.auto_approve = True  # Dream mode is fully autonomous

    # Rebuild agent with new settings
    if hasattr(app, 'agent'):
        from .agent import Agent
        app.agent = Agent(app.cfg)
        app.agent.rebuild_system()

    app.refresh_status()

    if arg.strip():
        app.log_user(f"/dream-ultra {arg.strip()}")
        app._run_agent_async(arg.strip())
        return ""

    return (f"🔥 DREAM MODE ULTRA PRO — Maximum Power!\n"
            f"Model: {app.cfg.model}\n"
            f"Max Tokens: {app.cfg.max_tokens}\n"
            f"Effort: 1000× Dream Mode\n"
            f"Plan Mode: ON\n"
            f"Auto-Test: ON\n\n"
            f"14 parallel analysis engines + 12 swarm agents:\n"
            f"  - Deep AST Analysis (complexity metrics)\n"
            f"  - Dependency Graph (circular detection)\n"
            f"  - Security Analysis (vulnerability scan)\n"
            f"  - Performance Analysis (inefficiency detection)\n"
            f"  - Code Quality Baseline (maintainability index)\n"
            f"  - Architecture Brain (coupling analysis)\n"
            f"  - Risk Heatmap (quantified risk scores)\n"
            f"  - Change Impact (blast radius)\n"
            f"  - Dead Code Detection\n"
            f"  - Type Hints Analysis\n"
            f"  - Code Smells Detection\n"
            f"  - API Surface Analysis\n"
            f"  - Test Coverage Analysis\n"
            f"  - Documentation Analysis\n\n"
            f"12 swarm agents for deep research:\n"
            f"  - Project structure analysis\n"
            f"  - Milestone breakdown\n"
            f"  - Risk identification\n"
            f"  - Dependency mapping\n"
            f"  - Conflict detection\n"
            f"  - Implementation optimization\n"
            f"  - Complexity estimation\n"
            f"  - Rollback strategy\n"
            f"  - Pattern review\n"
            f"  - Security validation\n"
            f"  - Verification planning\n"
            f"  - Success criteria\n\n"
            f"Type your goal to start DREAM MODE ULTRA PRO!")


def _stats(app, arg: str) -> str:
    """Show LLM client stats including cache hit rate."""
    from .llm.client import get_cache_stats
    agent_stats = app.agent.stats()
    cache = get_cache_stats()
    return (
        f"Agent Stats:\n"
        f"  Input tokens : {agent_stats['input_tokens']}\n"
        f"  Output tokens: {agent_stats['output_tokens']}\n"
        f"  Total tokens : {agent_stats['input_tokens'] + agent_stats['output_tokens']}\n"
        f"  Messages     : {agent_stats['messages']}\n"
        f"\nLLM Cache:\n"
        f"  Hits  : {cache['hits']}\n"
        f"  Misses: {cache['misses']}\n"
        f"  Rate  : {cache['hit_rate']}\n"
        f"  Size  : {cache['size']} entries"
    )


def _clear_cache(app, arg: str) -> str:
    """Clear the LLM response cache."""
    from .llm.client import clear_cache
    clear_cache()
    return "LLM cache cleared."

COMMANDS: list[SlashCommand] = [
    SlashCommand("/help",   "Show all commands",                     _help),
    SlashCommand("/init",   "Create a BITTU.md project guide",       _init),
    SlashCommand("/model",  "Show or set the AI model",              _model),
    SlashCommand("/mode",   "Switch mode: plan | build | chat",      _mode),
    SlashCommand("/cwd",    "Show or change working directory",      _cwd),
    SlashCommand("/config", "Show current configuration",            _config),
    SlashCommand("/tools",  "List available tools",                  _tools),
    SlashCommand("/login",  "Set API key / provider",                _login),
    SlashCommand("/setkey", "Save API key to config file",           _setkey),
    SlashCommand("/yolo",   "Toggle auto-approve for actions",       _yolo),
    SlashCommand("/clear",  "Clear the conversation",                _clear),
    # --- advanced ---
    SlashCommand("/undo",     "Undo last file change",               _undo),
    SlashCommand("/redo",     "Redo last undone change",             _redo),
    SlashCommand("/sessions", "List saved sessions",                 _sessions),
    SlashCommand("/resume",   "Resume a session (<id> | last)",      _resume),
    SlashCommand("/search",   "Semantic file search",                _search),
    SlashCommand("/index",    "Rebuild the codebase index",          _index),
    SlashCommand("/memory",   "Show remembered facts",               _memory),
    SlashCommand("/cost",     "Show token/cost usage",               _cost),
    SlashCommand("/git",      "Run a git command",                   _git),
    # --- new 18 advanced ---
    SlashCommand("/plan",        "Toggle plan-first mode",           _plan),
    SlashCommand("/autotest",    "Toggle auto-test after edits",     _autotest),
    SlashCommand("/checkpoint",  "Snapshot whole project",           _checkpoint),
    SlashCommand("/restore",     "Restore a project checkpoint",     _restore),
    SlashCommand("/checkpoints", "List project checkpoints",         _checkpoints),
    SlashCommand("/swarm",       "Run parallel sub-agents (a|b|c)",  _swarm),
    SlashCommand("/export",      "Export chat (md|html)",            _export),
    SlashCommand("/metrics",     "Code metrics (LOC, langs)",        _metrics),
    SlashCommand("/secrets",     "Scan for hardcoded secrets",       _secrets),
    SlashCommand("/todos",       "Find TODO/FIXME comments",         _todos),
    SlashCommand("/tree",        "Show project tree",                _tree),
    SlashCommand("/history",     "Show recent command history",      _history),
    # --- effort engine ---
    SlashCommand("/effort",         "Show/set effort level",         _effort),
    SlashCommand("/max",            "Max thinking — best work",      _max),
    SlashCommand("/ultra",          "Ultra thinking — complex work", _ultra),
    SlashCommand("/ultracombomax",  "Enterprise-level heavy work",   _ultracombomax),
    SlashCommand("/goal",           "Autonomous end-to-end goal",    _goal),
    SlashCommand("/dream",          "1000× — orchestrate EVERYTHING", _dream),
    SlashCommand("/dream-fast",     "Dream Mode + auto fast model",  _dream_fast),
    SlashCommand("/dream-ultra",    "Dream Mode ULTRA PRO",          _dream_ultra),
    SlashCommand("/stats",          "LLM cache + token stats",       _stats),
    SlashCommand("/clear-cache",    "Clear LLM response cache",      _clear_cache),
    SlashCommand("/quit",           "Exit BITTU",                    _quit),
]

REGISTRY = {c.name: c for c in COMMANDS}


def match(prefix: str) -> list[SlashCommand]:
    """Return commands whose name starts with `prefix` (for autocomplete)."""
    p = prefix.strip().lower()
    return [c for c in COMMANDS if c.name.startswith(p)]
