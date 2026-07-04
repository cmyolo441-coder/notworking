"""BITTU entry point.

    python -m zedpy                 # Grok-style TUI (default) — BITTU interface
    python -m zedpy --plain         # simple line-based REPL (no TUI)
    python -m zedpy -p "read README"# one prompt, then exit (plain)
    python -m zedpy --yolo          # auto-approve actions
    python -m zedpy --workdir /path # work on another directory
"""
from __future__ import annotations
import argparse
import os
import sys

from .config import Config


def _plain_repl(cfg: Config, one_shot: str = "") -> int:
    """Fallback line-based REPL (no TUI) — same agent underneath."""
    from .agent import Agent
    from .llm import LLMError

    agent = Agent(cfg)
    print(f"\n  BITTU (plain) · model: {cfg.model} · dir: {cfg.workdir}\n")

    if one_shot:
        try:
            print(agent.run(one_shot))
            return 0
        except LLMError as e:
            print(f"  LLM error: {e}", file=sys.stderr)
            return 1

    while True:
        try:
            user = input("\n› ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  bye 👋")
            return 0
        if not user:
            continue
        if user.lower() in ("exit", "quit", ":q"):
            print("  bye 👋")
            return 0
        try:
            print(f"\n{agent.run(user)}")
        except LLMError as e:
            print(f"  LLM error: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="zedpy", description="BITTU — Grok-style terminal AI agent.")
    parser.add_argument("--workdir", default=os.getcwd())
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--yolo", action="store_true", help="Auto-approve all actions.")
    parser.add_argument("--plain", action="store_true", help="Use the plain REPL instead of the TUI.")
    parser.add_argument("-p", "--prompt", default="", help="One prompt, then exit (implies --plain).")
    args = parser.parse_args()

    cfg = Config.load()
    cfg.workdir = os.path.abspath(args.workdir)
    if args.model:
        cfg.model = args.model
    if args.base_url:
        cfg.base_url = args.base_url
    if args.yolo:
        cfg.auto_approve = True

    if args.prompt or args.plain:
        return _plain_repl(cfg, args.prompt)

    # Default: launch the Grok-style TUI.
    # mouse=True taaki scroll-wheel + mouse events transcript ko milein.
    from .tui import BittuApp
    app = BittuApp(cfg)
    app.run(mouse=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
