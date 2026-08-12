"""BITTU launcher.

The launcher intentionally stays small: it validates the local runtime, keeps the
user's command line intact, and delegates application behavior to ``zedpy``.

Examples::

    python main.py                 # interactive TUI
    python main.py --plain         # line-based REPL
    python main.py -p "read README.md"
    python main.py --health        # local configuration/runtime diagnostics
    python main.py --version
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _has_textual() -> bool:
    """Return whether the optional TUI dependency is importable."""
    return importlib.util.find_spec("textual") is not None


def _install_textual() -> bool:
    """Offer an explicit, bounded dependency installation.

    The previous launcher mutated ``sys.argv`` and silently switched modes after
    an install failure. This implementation never hides the user's arguments and
    never installs anything unless the user explicitly confirms.
    """
    print("BITTU TUI requires the 'textual' package.")
    try:
        answer = input("Install it now with pip? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"
    if answer not in {"", "y", "yes"}:
        return False
    print("Installing textual…")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", "textual"],
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return False
    if completed.returncode == 0 and _has_textual():
        return True
    print("Installation failed. Use --plain or install textual manually.", file=sys.stderr)
    return False


def _is_tui_request(args: Sequence[str]) -> bool:
    """Determine whether the command intends to open the interactive TUI."""
    tui_bypass = {"--plain", "-p", "--prompt", "--help", "-h", "--version", "--health", "--update"}
    return not any(arg in tui_bypass for arg in args)


def _forward(args: list[str], *, force_plain: bool = False) -> int:
    """Delegate to the package entry point without losing command-line values."""
    from zedpy.__main__ import main as zedpy_main

    original = sys.argv
    try:
        forwarded = list(args)
        if force_plain and "--plain" not in forwarded and "-p" not in forwarded and "--prompt" not in forwarded:
            forwarded.insert(0, "--plain")
        sys.argv = [original[0], *forwarded]
        return int(zedpy_main())
    finally:
        sys.argv = original


def main(argv: Sequence[str] | None = None) -> int:
    """Run BITTU while preserving the historical ``python main.py`` contract."""
    args = list(sys.argv[1:] if argv is None else argv)

    # Help, version, health, update and plain/prompt paths do not require Textual.
    if _is_tui_request(args) and not _has_textual():
        if "--no-install" not in args:
            _install_textual()
        if not _has_textual():
            print("Starting plain mode because Textual is unavailable.", file=sys.stderr)
            args = [arg for arg in args if arg != "--no-install"]
            return _forward(args, force_plain=True)

    # ``--no-install`` belongs to this launcher only; do not leak it downstream.
    args = [arg for arg in args if arg != "--no-install"]
    return _forward(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nBITTU stopped.")
        raise SystemExit(130)
