"""Safe, bounded git operations for the project repository."""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from .base import Tool

_ALLOWED = {"status", "diff", "log", "add", "commit", "branch", "show", "stash", "restore", "checkout"}
_MUTATING = {"add", "commit", "stash", "restore", "checkout"}
_MAX_ARGS = 8_000
_MAX_OUTPUT = 15_000


class GitTool(Tool):
    name = "git"
    description = (
        "Git operations: status, diff, log, add, commit, branch, show, stash, "
        "restore, checkout. action=subcommand and args=extra arguments."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "git subcommand."},
                "args": {"type": "string", "description": "Extra arguments (optional)."},
            },
            "required": ["action"],
        }

    def run(self, workdir: str, action: str, args: str = "", **_) -> str:
        action = (action or "").strip().lower()
        if action not in _ALLOWED:
            return f"Error: git '{action}' allowed nahi. Allowed: {', '.join(sorted(_ALLOWED))}"
        if len(args or "") > _MAX_ARGS:
            return "Error: git arguments too long"
        try:
            cwd = Path(workdir).expanduser().resolve(strict=True)
            if not cwd.is_dir():
                return "Error: git workdir directory nahi hai"
            parsed_args = shlex.split(args or "")
        except (OSError, ValueError) as exc:
            return f"Error: invalid git arguments/workdir: {exc}"

        # Git's -c/--exec-path/--upload-pack options can execute or redirect
        # helpers. They are deliberately excluded from agent-generated args.
        forbidden = {"-c", "--exec-path", "--upload-pack", "--receive-pack", "--config-env"}
        if any(item in forbidden or any(item.startswith(flag + "=") for flag in forbidden if flag.startswith("--")) for item in parsed_args):
            return "Error: git helper/config override arguments are not allowed"
        argv = ["git", "--no-pager", action] + parsed_args
        env = os.environ.copy()
        env.update({"GIT_PAGER": "cat", "GIT_TERMINAL_PROMPT": "0"})
        try:
            proc = subprocess.run(
                argv, cwd=str(cwd), env=env, capture_output=True,
                text=True, errors="replace", timeout=60, check=False,
            )
        except FileNotFoundError:
            return "Error: git installed nahi hai."
        except subprocess.TimeoutExpired:
            return "Error: git command 60s timeout par stop hua"
        output = (proc.stdout or "") + (proc.stderr or "")
        if len(output) > _MAX_OUTPUT:
            output = output[:_MAX_OUTPUT] + "\n…[truncated]"
        suffix = " [mutating action]" if action in _MUTATING else ""
        return f"$ {' '.join(shlex.quote(part) for part in argv)}{suffix}\n(exit {proc.returncode})\n{output}".rstrip()
