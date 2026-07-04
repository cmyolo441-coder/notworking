"""ReAct agent engine — advanced autonomous reasoning with self-healing.

Features:
  - Multi-step reasoning: explicit plan → implement → verify cycle
  - Context compression: auto-summarize when context window fills
  - Auto-debug loops: retry failures up to max_debug_retries times
  - Adaptive planning: plan depth adjusts to effort level
  - Tool chain composition: chain tool results into next steps
  - Incremental verification: verify after EACH change, not just at end
  - Self-healing: detect failures and auto-repair
"""
from __future__ import annotations
import json
import threading
import time

from .config import Config
from .llm import LLM, LLMError
from .llm.streaming import stream_chat
from .tools import REGISTRY, SCHEMAS
from .core.index import CodeIndex
from .core.memory import MEMORY
from .core import effort as effort_engine
from .systemprompts import (
    MAIN_SYSTEM_PROMPT, GOAL_CONTRACT, PLAN_MODE_PROMPT, AUTO_TEST_PROMPT,
)


# === INSTRUCTION REINFORCEMENT PROMPTS ===
COMPLIANCE_REMINDER = (
    "[COMPLIANCE CHECK] Remember your MANDATORY RULES:\n"
    "1. READ files BEFORE editing (read_file, grep)\n"
    "2. Use edit_file (surgical) NOT write_file for existing files\n"
    "3. VERIFY after changes (run tests with run_shell)\n"
    "4. USE TOOLS to do work — don't just describe actions\n"
    "5. Fix any errors immediately\n"
    "Violating these rules is NOT allowed. Follow them now."
)

POST_TOOL_REMINDER = (
    "[REMINDER] You are BITTU, a software engineering AGENT. "
    "Use tools to DO work, not describe it. "
    "After edits, ALWAYS verify with tests (run_shell). "
    "If you see errors, fix them before continuing."
)


class Agent:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.llm = LLM(cfg)
        self.index = CodeIndex(cfg.workdir)
        self.effort = effort_engine.get(getattr(cfg, "effort", "normal"))
        self.history: list[dict] = [{"role": "system", "content": self._system()}]
        self._auto_context_done = False
        self._debug_fails = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.cancel_event = threading.Event()
        # Context window tracking
        self._approx_tokens = 0
        self._compress_threshold = getattr(cfg, "context_window_limit", 200_000)
        # Instruction reinforcement tracking
        self._tool_call_count = 0
        self._last_reinforcement_step = 0
        self._reinforcement_interval = 5  # Inject reminder every N tool calls

    def set_effort(self, name: str) -> str:
        """Switch effort level at runtime; rebuild system prompt."""
        self.effort = effort_engine.get(name)
        self.rebuild_system()
        return (f"Effort -> {self.effort.label} "
                f"({self.effort.multiplier}x . {self.effort.max_steps} steps)")

    # --- system prompt + remembered context ---
    def _system(self) -> str:
        base = MAIN_SYSTEM_PROMPT
        eff = getattr(self, "effort", None)
        if eff is not None:
            base += f"\n\n=== EFFORT: {eff.label} ({eff.multiplier}x) ===\n{eff.description}"
            if eff.extra_prompt:
                base += "\n" + eff.extra_prompt
        if self.cfg.plan_mode:
            base += ("\n\n" + PLAN_MODE_PROMPT)
        if self.cfg.auto_test:
            base += "\n\n" + AUTO_TEST_PROMPT
        mem = MEMORY.context_block()
        return base + ("\n\n" + mem if mem else "")

    def rebuild_system(self) -> None:
        """Re-apply system prompt when a mode flag changes."""
        if self.history and self.history[0].get("role") == "system":
            self.history[0]["content"] = self._system()

    def _append_history(self, role: str, content: str = "",
                        tool_calls: list | None = None,
                        tool_call_id: str = "", name: str = "") -> None:
        """Centralized history append with context window tracking."""
        msg: dict = {"role": role}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if name:
            msg["name"] = name
        self.history.append(msg)
        # Track approximate token count
        self._approx_tokens += len(str(content)) // 4 + 20

    def _inject_reinforcement(self) -> None:
        """Inject compliance reminder periodically to keep LLM on track."""
        if self._tool_call_count - self._last_reinforcement_step >= self._reinforcement_interval:
            self._last_reinforcement_step = self._tool_call_count
            self._append_history("user", COMPLIANCE_REMINDER)

    def _post_tool_reminder(self) -> None:
        """Inject a brief reminder after tool calls to maintain instruction adherence."""
        self._append_history("user", POST_TOOL_REMINDER)

    def _check_tool_usage_compliance(self, msg: dict) -> bool:
        """Check if LLM is trying to describe work instead of using tools.
        Returns True if compliance injection was added."""
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        
        # If no tools called but response contains action phrases, inject reminder
        if not tool_calls and content:
            action_phrases = [
                "i'll create", "i'll write", "i'll add", "i'll modify",
                "you should", "we need to", "let me", "i can",
                "the file should", "create a file", "write a file",
            ]
            content_lower = content.lower()
            if any(phrase in content_lower for phrase in action_phrases):
                self._append_history("user",
                    "[AGENT COMPLIANCE] You described work instead of doing it. "
                    "You are an AGENT with tools. USE THEM. "
                    "Call write_file, edit_file, or run_shell to actually do the work. "
                    "Do NOT just describe what to do.")
                return True
        return False

    def _maybe_compress_context(self) -> None:
        """Auto-compress history when context window fills up.

        Strategy: summarize old messages and replace with a compact summary,
        keeping the most recent messages intact.
        """
        if self._approx_tokens < self._compress_threshold:
            return
        if not getattr(self.effort, "context_compression", False):
            return

        # Keep system prompt + last N messages, summarize the middle
        keep_recent = 10
        if len(self.history) <= keep_recent + 2:
            return

        system = self.history[0]
        middle = self.history[1:-keep_recent]
        recent = self.history[-keep_recent:]

        # Build summary of middle messages
        summary_parts = []
        for msg in middle:
            role = msg.get("role", "")
            content = msg.get("content") or ""
            if role == "system":
                continue
            if content and not content.startswith("["):
                summary_parts.append(f"{role}: {content[:200]}")

        if summary_parts:
            summary = "[CONTEXT COMPRESSED] Earlier conversation summary:\n"
            summary += "\n".join(summary_parts[-10:])  # Last 10 exchanges
            # Always re-inject system prompt compliance reminder after compression
            summary += (
                "\n\n[CRITICAL] Context was compressed. Your MANDATORY RULES still apply:\n"
                "1. READ files BEFORE editing\n"
                "2. Use edit_file for surgical edits\n"
                "3. VERIFY after changes with tests\n"
                "4. USE TOOLS to do work, don't just describe\n"
                "Follow these rules. You are an AGENT, not a chatbot."
            )
            self.history = [system, {"role": "user", "content": summary}] + recent
            self._approx_tokens = len(str(self.history)) // 4
            # Reset reinforcement counter after compression
            self._last_reinforcement_step = self._tool_call_count

    def _approve(self, tool, args: dict) -> bool:
        if getattr(self.effort, "auto_accept", False):
            return True
        if self.cfg.auto_approve or not getattr(tool, "requires_approval", False):
            return True
        cb = getattr(self, "_approve_cb", None)
        if cb is not None:
            return cb(tool.name, args)
        preview = json.dumps(args, ensure_ascii=False)[:400]
        print(f"\n  Warning: '{tool.name}': {preview}")
        try:
            return input("  Allow? [y/N] ").strip().lower() in ("y", "yes")
        except EOFError:
            return False

    # --- auto-context injection ---
    def _inject_context(self, user_input: str) -> None:
        """On first turn, inject relevant files into context."""
        if self._auto_context_done:
            return
        self._auto_context_done = True
        limit = getattr(self.effort, "context_files", 3)
        try:
            hits = self.index.search(user_input, limit=limit)
        except Exception:
            return
        if not hits:
            return
        block = "[AUTO-CONTEXT] These files seem relevant:\n"
        block += "\n".join(f"  - {rel} (relevance {score})" for rel, score in hits)
        block += "\nRead them with read_file if needed."
        self._append_history("user", block)

    # --- main loop ---
    def run(self, user_input: str, on_text=None) -> str:
        """Process one message. on_text(delta) enables streaming."""
        self._append_history("user", user_input)
        self._inject_context(user_input)
        self.cancel_event.clear()
        self._debug_fails = 0

        # Context compression check
        self._maybe_compress_context()

        # DREAM MODE: full control plane
        if getattr(self.effort, "dream_mode", False):
            try:
                from .core import dream
                self._append_history("user",
                                     dream.control_plane(self.cfg, user_input))
            except Exception:
                pass
        # GOAL MODE: inject execution contract
        elif getattr(self.effort, "goal_mode", False):
            self._append_history("user",
                                     GOAL_CONTRACT + user_input)
        # Effort preflight (skip if dream already ran control plane)
        if not getattr(self.effort, "dream_mode", False):
            self._effort_preflight(user_input)

        # Max steps from effort level
        max_steps = max(self.cfg.max_steps,
                        getattr(self.effort, "max_steps", 80))

        for step in range(max_steps):
            if self.cancel_event.is_set():
                return "Stopped by user (Esc)."

            # Streaming or non-streaming LLM call
            if on_text is not None:
                msg = stream_chat(self.cfg, self.history, SCHEMAS, on_text,
                                  cancel_event=self.cancel_event)
            else:
                msg = self.llm.chat(self.history, tools=SCHEMAS)
            self._track(msg)

            tool_calls = msg.get("tool_calls") or []
            self._append_history(
                "assistant",
                content=msg.get("content") or "",
                tool_calls=tool_calls,
            )

            if not tool_calls:
                # Check if LLM is describing work instead of doing it
                if self._check_tool_usage_compliance(msg):
                    continue  # Re-loop with compliance reminder injected
                answer = msg.get("content") or "(no response)"
                return self._finalize(answer)

            # Execute tool calls
            for call in tool_calls:
                if self.cancel_event.is_set():
                    return "Stopped by user (Esc)."
                result = self._execute_tool(call)
                self._tool_call_count += 1
                self._append_history(
                    "tool",
                    content=result,
                    tool_call_id=call.get("id", ""),
                    name=call.get("function", {}).get("name", ""),
                )
                # Post-tool reminder to keep agent on track
                if self._tool_call_count % 3 == 0:
                    self._post_tool_reminder()
            # Periodic compliance reinforcement
            self._inject_reinforcement()

            # Auto-test after file changes
            if self.cfg.auto_test and self._changed_files(tool_calls):
                self._run_auto_test()

            # Effort gates: quality/security checks after changes
            if self._changed_files(tool_calls):
                self._effort_gates()

            # Self-healing: if agent detected a failure, retry
            if getattr(self.effort, "self_healing", False):
                self._self_heal_check()

        return "Max steps reached."

    def _execute_tool(self, call: dict) -> str:
        """Execute a single tool call with approval + error handling."""
        fn = call.get("function", {})
        name = fn.get("name", "")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}

        tool = REGISTRY.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        if not self._approve(tool, args):
            return "Error: user denied the action."

        shown = ", ".join(f"{k}={v!r}"[:50] for k, v in args.items())
        disp = getattr(self, "_tool_cb", None)
        if disp is not None:
            disp(f"{name}({shown})")
        else:
            print(f"  -> {name}({shown})")

        try:
            result = tool.run(self.cfg.workdir, **args)
        except Exception as e:
            result = f"Error: {e}"

        res_cb = getattr(self, "_tool_result_cb", None)
        if res_cb is not None:
            res_cb(name, result)
        return result

    # --- finalization: dream/goal verification + evidence ---
    def _finalize(self, answer: str) -> str:
        e = self.effort
        if getattr(e, "dream_mode", False):
            try:
                from .core import dream
                plane = dream.verification_plane(self.cfg, self.history)
                answer += "\n\n" + "-" * 40 + "\n" + plane
            except Exception:
                pass
        elif getattr(e, "export_evidence", False):
            try:
                from .core.export import export
                answer += "\n\n" + export(self.history, self.cfg.workdir, "md")
            except Exception:
                pass
        return answer

    # --- effort preflight (before acting) ---
    def _effort_preflight(self, user_input: str) -> None:
        e = self.effort
        if not e.enterprise_preflight:
            return
        blocks: list[str] = []

        if e.auto_checkpoint:
            try:
                from .core import checkpoint
                blocks.append(checkpoint.create(self.cfg.workdir))
            except Exception:
                pass
        if e.run_metrics:
            try:
                blocks.append("## metrics\n" +
                              REGISTRY["code_metrics"].run(self.cfg.workdir)[:1500])
            except Exception:
                pass
        if e.run_security:
            try:
                blocks.append("## secret_scan\n" +
                              REGISTRY["secret_scan"].run(self.cfg.workdir)[:1500])
            except Exception:
                pass
        if e.deep_research:
            try:
                blocks.append("## deps\n" +
                              REGISTRY["deps"].run(self.cfg.workdir)[:1200])
            except Exception:
                pass
        if e.use_swarm:
            try:
                from .core.swarm import run_swarm
                subtasks = [
                    f"Key steps to accomplish: {user_input}",
                    f"Main risks/edge cases for: {user_input}",
                ]
                blocks.append(
                    run_swarm(self.cfg, subtasks,
                              max_workers=e.swarm_size or 2)[:2000])
            except Exception:
                pass
        if blocks:
            self._append_history("user",
                f"[EFFORT PREFLIGHT - {e.label}] Real local evidence. "
                "Use this to plan carefully:\n\n" + "\n\n".join(blocks))

    # --- effort gates (after changes) ---
    def _effort_gates(self) -> None:
        e = self.effort
        if not (e.run_quality or e.run_security or e.enterprise_gates):
            return
        findings: list[str] = []

        if e.run_security:
            try:
                out = REGISTRY["secret_scan"].run(self.cfg.workdir)
                if "No secrets" not in out:
                    findings.append("SECURITY:\n" + out[:1500])
            except Exception:
                pass
        if e.run_quality:
            import os
            for f in os.listdir(self.cfg.workdir):
                if f.endswith(".py"):
                    try:
                        out = REGISTRY["lint"].run(self.cfg.workdir, path=f)
                        if "no issues" not in out.lower() and "ok" not in out.lower():
                            findings.append(out[:800])
                    except Exception:
                        pass
                    break
        if findings:
            self._append_history("user",
                "[EFFORT GATES] Auto-checks found issues. "
                "Fix them before finishing:\n\n" + "\n\n".join(findings))

    # --- self-healing check ---
    def _self_heal_check(self) -> None:
        """Detect if last tool calls produced errors and inject retry prompt."""
        max_retries = getattr(self.effort, "max_debug_retries", 0)
        if max_retries <= 0:
            return

        # Check last few history entries for errors
        error_count = 0
        for msg in self.history[-6:]:
            content = msg.get("content") or ""
            if msg.get("role") == "tool" and content.startswith("Error:"):
                error_count += 1

        if error_count >= 2 and self._debug_fails < max_retries:
            self._debug_fails += 1
            self._append_history("user",
                f"[SELF-HEAL] Detected {error_count} consecutive errors "
                f"(attempt {self._debug_fails}/{max_retries}). "
                "Diagnose the root cause and try a different approach.")

    # --- auto-test after file changes ---
    def _changed_files(self, tool_calls) -> bool:
        return any(c.get("function", {}).get("name") in
                   ("write_file", "edit_file", "append_file", "regex_replace")
                   for c in tool_calls)

    def _detect_test_command(self) -> str:
        if self.cfg.test_command:
            return self.cfg.test_command
        import os
        wd = self.cfg.workdir
        if any(f.startswith("test_") or f.endswith("_test.py")
               for f in os.listdir(wd) if os.path.isfile(os.path.join(wd, f))):
            return ("python3 -m pytest -q 2>/dev/null || "
                    "python3 -m unittest 2>&1 | tail -20")
        return ""

    def _run_auto_test(self) -> None:
        cmd = self._detect_test_command()
        if not cmd:
            return
        try:
            out = REGISTRY["run_shell"].run(self.cfg.workdir,
                                            command=cmd,
                                            timeout_seconds=90)
        except Exception:
            return
        failed = any(w in out.lower()
                     for w in ("fail", "error", "traceback"))
        if failed:
            self._append_history("user",
                "[AUTO-TEST] Tests failed after your changes. "
                "Fix them:\n\n" + out[:4000])

    # --- token tracking ---
    def _track(self, msg: dict) -> None:
        u = msg.get("_usage") or {}
        self.total_input_tokens += u.get("prompt_tokens", 0)
        self.total_output_tokens += u.get("completion_tokens", 0)

    def stats(self) -> dict:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "messages": len(self.history),
        }
