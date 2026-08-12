"""Controlled project shell execution with explicit safety boundaries."""
from __future__ import annotations

import os
import re
import signal
import subprocess
from pathlib import Path

from .base import Tool


_BLOCKED = [
    re.compile(r"\brm\s+-[a-z]*r[a-z]*f[a-z]*(?:\s+--)?\s+(?:/|~)(?:\s|$)", re.I),
    re.compile(r"\brm\s+-[a-z]*f[a-z]*r[a-z]*(?:\s+--)?\s+(?:/|~)(?:\s|$)", re.I),
    re.compile(r":\s*\(\s*\)\s*\{.*\}\s*;", re.S),
    re.compile(r"\bmkfs(?:\.[\w-]+)?\b", re.I),
    re.compile(r"\bdd\s+[^\n;]*\bof\s*=\s*/dev/", re.I),
    re.compile(r"(?:>|>>|\s)\s*/dev/(?:sd[a-z]|nvme\d+n\d+|mmcblk\d+)", re.I),
    re.compile(r"\b(?:shutdown|poweroff|reboot|halt)\b", re.I),
    re.compile(r"\bchmod\s+(-R\s+)?777\s+/", re.I),
]
_MAX_COMMAND = 32_000
_MAX_OUTPUT = 20_000
_MIN_TIMEOUT = 1
_MAX_TIMEOUT = 900


def _blocked(command: str) -> bool:
    return any(pattern.search(command) for pattern in _BLOCKED)


def _truncate(output: str) -> str:
    if len(output) <= _MAX_OUTPUT:
        return output
    head = _MAX_OUTPUT * 3 // 4
    tail = _MAX_OUTPUT - head
    return output[:head] + f"\n…[output truncated: {len(output) - _MAX_OUTPUT} chars]…\n" + output[-tail:]


class RunShell(Tool):
    name = "run_shell"
    description = (
        "Project directory me shell command chalao aur combined stdout/stderr + exit "
        "code return karo. Build, test, run, git etc. ke liye; destructive commands blocked hain."
    )
    requires_approval = True

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command."},
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Timeout in seconds (1-900, default 120).",
                },
            },
            "required": ["command"],
        }

    def run(self, workdir: str, command: str, timeout_seconds: int = 120, **_) -> str:
        cmd = (command or "").strip()
        if not cmd:
            return "Error: empty command"
        if len(cmd) > _MAX_COMMAND:
            return f"Error: command {_MAX_COMMAND} characters se zyada hai"
        if _blocked(cmd):
            return f"BLOCKED: destructive command run nahi hui: {cmd}"
        try:
            cwd = Path(workdir).expanduser().resolve(strict=True)
            if not cwd.is_dir():
                return f"Error: workdir directory nahi hai: {workdir}"
        except OSError as exc:
            return f"Error: invalid workdir: {exc}"
        try:
            timeout = max(_MIN_TIMEOUT, min(int(timeout_seconds or 120), _MAX_TIMEOUT))
        except (TypeError, ValueError):
            return "Error: timeout_seconds integer hona chahiye"

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                executable="/bin/bash",
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                start_new_session=True,
            )
            output, _ = proc.communicate(timeout=timeout)
            return f"$ {cmd}\n(exit code: {proc.returncode})\n{_truncate(output or '')}".rstrip()
        except subprocess.TimeoutExpired:
            if proc is not None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.communicate(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except OSError:
                        pass
            return f"$ {cmd}\n(exit code: timeout)\nError: command {timeout}s me timeout hua aur process group terminate kiya gaya"
        except (OSError, ValueError) as exc:
            return f"Error: run fail: {exc}"
        finally:
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass
