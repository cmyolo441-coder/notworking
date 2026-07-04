"""Feature 5 — Git integration tool.

Agent ko git operations dega: status, diff, log, add, commit, branch.
Sirf whitelisted subcommands (safe). shell=False (injection-safe).
"""
from __future__ import annotations

import subprocess

from .base import Tool

_ALLOWED = {"status", "diff", "log", "add", "commit", "branch",
            "show", "stash", "restore", "checkout"}


class GitTool(Tool):
    name = "git"
    description = (
        "Git operations: status, diff, log, add, commit, branch, show. "
        "action = subcommand (e.g. 'status'), args = extra args string "
        "(e.g. '-m \"fix bug\"' for commit)."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "git subcommand (status/diff/log/add/commit/branch/show)."},
                "args": {"type": "string", "description": "Extra arguments (optional)."},
            },
            "required": ["action"],
        }

    def run(self, workdir: str, action: str, args: str = "", **_) -> str:
        action = (action or "").strip()
        if action not in _ALLOWED:
            return f"Error: git '{action}' allowed nahi. Allowed: {', '.join(sorted(_ALLOWED))}"
        import shlex
        try:
            argv = ["git", action] + shlex.split(args)
        except ValueError as e:
            return f"Error: bad args: {e}"
        try:
            proc = subprocess.run(argv, cwd=workdir, capture_output=True,
                                  text=True, timeout=60)
        except FileNotFoundError:
            return "Error: git installed nahi hai."
        except subprocess.TimeoutExpired:
            return "Error: git command timeout"
        out = (proc.stdout or "") + (proc.stderr or "")
        if len(out) > 15000:
            out = out[:15000] + "\n…[truncated]"
        return f"$ {' '.join(argv)}\n(exit {proc.returncode})\n{out}".rstrip()
