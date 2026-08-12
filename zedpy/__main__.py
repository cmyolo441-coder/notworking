"""Command-line entry point for BITTU.

The TUI remains the default, while plain mode is deterministic and useful for
scripts, CI smoke checks, and environments without terminal rendering support.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .config import Config


def _plain_repl(cfg: Config, one_shot: str = "") -> int:
    """Run the line-based REPL or one-shot prompt."""
    from .agent import Agent
    from .llm import LLMError

    if not cfg.api_key:
        print(
            "BITTU needs an API key for plain mode. Set ZEDPY_API_KEY, "
            "OPENCODE_API_KEY, NVIDIA_API_KEY, or CF_API_KEY.",
            file=sys.stderr,
        )
        return 2

    agent = Agent(cfg)
    print(f"\n  BITTU (plain) · model: {cfg.model} · dir: {cfg.workdir}\n")

    if one_shot:
        try:
            print(agent.run(one_shot))
            return 0
        except LLMError as exc:
            print(f"  LLM error: {exc}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\n  cancelled", file=sys.stderr)
            return 130

    while True:
        try:
            user = input("\n› ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  bye")
            return 0
        if not user:
            continue
        if user.lower() in {"exit", "quit", ":q"}:
            print("  bye")
            return 0
        try:
            print(f"\n{agent.run(user)}")
        except LLMError as exc:
            print(f"  LLM error: {exc}", file=sys.stderr)
        except KeyboardInterrupt:
            agent.cancel_event.set()
            print("\n  cancelled", file=sys.stderr)


def _health(cfg: Config, *, as_json: bool = False) -> int:
    """Print local, non-network runtime diagnostics."""
    parsed = urlparse(cfg.base_url)
    payload = {
        "version": __version__,
        "python": sys.version.split()[0],
        "workdir": cfg.workdir,
        "workdir_exists": Path(cfg.workdir).is_dir(),
        "model": cfg.model,
        "provider_host": parsed.netloc or None,
        "api_key_configured": bool(cfg.api_key),
        "textual_available": _textual_available(),
        "max_steps": cfg.max_steps,
        "max_tokens": cfg.max_tokens,
        "timeout_seconds": cfg.timeout,
        "effort": cfg.effort,
        "cache_enabled": cfg.enable_caching,
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("BITTU health")
        for key, value in payload.items():
            print(f"  {key:22} {value}")
    return 0 if payload["workdir_exists"] else 1


def _textual_available() -> bool:
    try:
        import textual  # noqa: F401
    except ImportError:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zedpy",
        description="BITTU — real-world terminal coding agent.",
    )
    parser.add_argument("--version", action="version", version=f"BITTU {__version__}")
    parser.add_argument("--workdir", default=os.getcwd(), help="Project directory to operate in.")
    parser.add_argument("--model", default="", help="Override the configured model id.")
    parser.add_argument("--base-url", default="", help="Override the OpenAI-compatible endpoint.")
    parser.add_argument("--effort", default="", help="Effort profile: normal, max, ultra, goal, dream.")
    parser.add_argument("--max-steps", type=int, default=None, help="Bound the ReAct loop steps.")
    parser.add_argument("--max-tokens", type=int, default=None, help="Bound the model output tokens.")
    parser.add_argument("--timeout", type=int, default=None, help="Network timeout in seconds.")
    parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature.")
    parser.add_argument("--no-cache", action="store_true", help="Disable the LLM response cache.")
    parser.add_argument("--yolo", action="store_true", help="Auto-approve actions (use only in a trusted workdir).")
    parser.add_argument("--plain", action="store_true", help="Use the plain REPL instead of the TUI.")
    parser.add_argument("-p", "--prompt", default="", help="Run one prompt, then exit (implies --plain).")
    parser.add_argument("--health", action="store_true", help="Print local configuration/runtime diagnostics.")
    parser.add_argument("--json", action="store_true", help="Format --health output as JSON.")
    parser.add_argument("--update", action="store_true", help="Update BITTU from GitHub.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.update:
        from .update import update
        return update()

    cfg = Config.load()
    requested_workdir = Path(args.workdir).expanduser()
    try:
        cfg.workdir = str(requested_workdir.resolve(strict=True))
        if not Path(cfg.workdir).is_dir():
            raise ValueError("not a directory")
    except (OSError, ValueError):
        parser.error(f"workdir is not a directory: {args.workdir}")

    if args.model:
        cfg.model = args.model.strip()
    if args.base_url:
        parsed = urlparse(args.base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            parser.error("--base-url must be an http(s) URL")
        cfg.base_url = args.base_url.strip().rstrip("/")
    if args.effort:
        cfg.effort = args.effort.strip().lower()
    if args.max_steps is not None:
        cfg.max_steps = max(1, min(args.max_steps, 500))
    if args.max_tokens is not None:
        cfg.max_tokens = max(256, min(args.max_tokens, 2_000_000))
    if args.timeout is not None:
        cfg.timeout = max(5, min(args.timeout, 3_600))
    if args.temperature is not None:
        cfg.temperature = max(0.0, min(args.temperature, 2.0))
    if args.no_cache:
        cfg.enable_caching = False
    if args.yolo:
        cfg.auto_approve = True
        cfg.yolo_mode = True

    if args.health:
        return _health(cfg, as_json=args.json)
    if args.json:
        parser.error("--json is only valid together with --health")

    if args.prompt or args.plain:
        return _plain_repl(cfg, args.prompt)

    if not _textual_available():
        print("Textual is not installed. Run: python -m pip install textual", file=sys.stderr)
        print("For a no-TUI run, use: python main.py --plain", file=sys.stderr)
        return 2

    from .tui import BittuApp
    app = BittuApp(cfg)
    try:
        app.run(mouse=True)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
