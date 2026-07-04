#!/usr/bin/env python3
"""BITTU — easy launcher.

Bas ye chalao:

    python main.py                 # BITTU TUI (Grok-style) kholo
    python main.py --plain         # simple line REPL (bina TUI)
    python main.py -p "read README"# ek prompt, phir exit
    python main.py --yolo          # sabhi actions auto-approve
    python main.py --workdir /path # doosri directory par kaam

Pehli baar? Ye script khud check karega ki `textual` installed hai ya nahi,
aur na ho to install karne ka option dega.
"""
from __future__ import annotations
import os
import subprocess
import sys

# Is folder ko import path me daalo taaki `zedpy` package mile,
# chahe kahin se bhi run karo.
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _ensure_textual() -> bool:
    """Return True if the TUI can run (textual available)."""
    try:
        import textual  # noqa: F401
        return True
    except ImportError:
        return False


def _try_install_textual() -> bool:
    print("  'textual' package nahi mila (TUI ke liye zaroori).")
    try:
        ans = input("  Abhi install kar du? [Y/n] ").strip().lower()
    except EOFError:
        ans = "n"
    if ans in ("", "y", "yes"):
        print("  Installing textual…")
        rc = subprocess.call([sys.executable, "-m", "pip", "install", "textual"])
        if rc == 0:
            print("  ✅ Installed!\n")
            return True
        print("  ❌ Install fail hua. Manually chalao:  pip install textual")
    return False


def main() -> int:
    # --plain / -p ke saath TUI ki zaroorat nahi — seedha delegate.
    args = sys.argv[1:]
    wants_tui = not any(a in ("--plain", "-p", "--prompt") for a in args)

    if wants_tui and not _ensure_textual():
        if _try_install_textual():
            if not _ensure_textual():
                print("  textual ab bhi load nahi hua — --plain mode use karo.")
                sys.argv.append("--plain")
        else:
            print("  TUI ke bina --plain mode me chala raha hoon…\n")
            sys.argv.append("--plain")

    # zedpy ka asli entry-point call karo (saare flags forward ho jaate hain).
    from zedpy.__main__ import main as zedpy_main
    return zedpy_main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  bye 👋")
        sys.exit(0)
