"""Shell tool: koi bhi shell command chalao (guardrails ke saath).

Do layer safety:
  1. BLOCKED regex -> destructive commands bilkul run nahi honge.
  2. requires_approval -> agent user se 'y' poochta hai (jab tak --yolo na ho).
"""
from __future__ import annotations

import re
import subprocess

from .base import Tool

BLOCKED = [
    re.compile(r"\brm\s+-rf\s+/(\s|$)"),      # rm -rf /
    re.compile(r"\brm\s+-rf\s+~"),            # rm -rf ~
    re.compile(r":\(\)\s*\{.*\}\s*;"),        # fork bomb
    re.compile(r"\bmkfs\b"),                  # filesystem format
    re.compile(r"\bdd\s+if=.*of=/dev/"),      # raw device write
    re.compile(r">\s*/dev/sd[a-z]"),          # disk clobber
    re.compile(r"\bshutdown\b"),
    re.compile(r"\breboot\b"),
]


class RunShell(Tool):
    name = "run_shell"
    description = (
        "Project directory me ek shell command chalao aur combined stdout/stderr "
        "+ exit code return karo. Build, test, run, git, etc. ke liye."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command."},
                "timeout_seconds": {"type": "integer", "description": "Optional timeout (default 120)."},
            },
            "required": ["command"],
        }

    def run(self, workdir: str, command: str, timeout_seconds: int = 120, **_) -> str:
        cmd = (command or "").strip()
        if not cmd:
            return "Error: empty command"
        for pat in BLOCKED:
            if pat.search(cmd):
                return f"BLOCKED: destructive command, run nahi hui: {cmd}"
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=workdir,
                capture_output=True, text=True,
                timeout=timeout_seconds or 120,
            )
        except subprocess.TimeoutExpired:
            return f"Error: command {timeout_seconds}s me timeout"
        except Exception as e:
            return f"Error: run fail: {e}"
        out = (proc.stdout or "") + (proc.stderr or "")
        if len(out) > 20000:
            out = out[:20000] + "\n…[output truncated]"
        return f"$ {cmd}\n(exit code: {proc.returncode})\n{out}".rstrip()
