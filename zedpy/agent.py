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
from .core import effort as effort_engine
from .core.index import CodeIndex
from .core.memory import MEMORY
from .llm import LLM
from .llm.streaming import stream_chat
from .systemprompts import (
    AUTO_TEST_PROMPT,
    GOAL_CONTRACT,
    MAIN_SYSTEM_PROMPT,
    PLAN_MODE_PROMPT,
)
from .tools import REGISTRY, SCHEMAS

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

# === DREAM MODE — bounded autonomous loop ===
# The loop keeps going (auto-continuing) until a REAL completion check passes,
# bounded so it can never run or cost forever:
#   - DREAM_HARD_CAP        : absolute ceiling on loop steps in dream mode.
#   - DREAM_CONTINUATION_CAP : max auto-continuations after the model stops.
#   - stall detection        : stop if no measurable progress for N rounds.
# Bounded autonomous execution: large jobs should be resumed in explicit turns,
# never allowed to run away indefinitely in a single provider session.
DREAM_HARD_CAP = 1_000
DREAM_CONTINUATION_CAP = 80
DREAM_STALL_LIMIT = 12
DREAM_FAKE_CACHE_TTL = 60.0 # seconds: reuse fake-scan result if mtime unchanged
DREAM_CONTINUATION_PROMPT = (
    "[DREAM — ENTERPRISE CONTINUATION] The goal is not verified complete yet. "
    "Continue with real tool calls while respecting the configured step cap, "
    "cancellation, retry budget, checkpoints and approval policy. Do not claim "
    "completion without evidence; if blocked, report the blocker and preserve "
    "resume state. Reason to continue: "
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
        # Dream bounded-loop state.
        self._dream_continuations = 0
        self._dream_stall = 0
        self._dream_last_state: tuple | None = None
        self._dream_mtime_snapshot: tuple | None = None
        # Persistent task ledger (Dream Mode source of truth). None until a
        # dream run creates/resumes it.
        self._ledger: dict | None = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.total_tool_calls = 0
        self.last_latency_ms = 0.0
        self.current_step = 0
        self._live_output_chars = 0
        self._live_input_estimate = 0
        self._telemetry_lock = threading.RLock()
        self.cancel_event = threading.Event()
        # Context window tracking
        self._approx_tokens = 0
        self._compress_threshold = getattr(cfg, "context_window_limit", 200_000)
        # Instruction reinforcement tracking
        self._tool_call_count = 0
        self._last_reinforcement_step = 0
        self._reinforcement_interval = 5  # Inject reminder every N tool calls
        # Test result cache (keyed by mtime snapshot to avoid redundant runs)
        self._tests_cache: tuple | None = None
        # Fake-scan result cache (keyed by mtime snapshot + TTL)
        self._fakes_cache: tuple | None = None

    def set_effort(self, name: str) -> str:
        """Switch effort level at runtime; rebuild system prompt."""
        self.effort = effort_engine.get(name)
        # Keep the provider request aligned with the selected execution mode.
        self.cfg.max_tokens = max(256, min(int(self.effort.max_tokens), 2_000_000))
        self.cfg.temperature = max(0.0, min(float(self.effort.temperature), 2.0))
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
            # Inject as assistant role to avoid consecutive user messages
            # which some models reject (user→user without assistant in between)
            self.history = [
                system,
                {"role": "user", "content": "[context compressed — see summary below]"},
                {"role": "assistant", "content": summary},
            ] + recent
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
        started_at = time.monotonic()
        with self._telemetry_lock:
            self.total_requests += 1
            self.current_step = 0
            self._live_output_chars = 0
            self._live_input_estimate = max(0, len(str(self.history)) // 4)
        self._append_history("user", user_input)
        self._inject_context(user_input)
        self.cancel_event.clear()
        self._debug_fails = 0
        # Reset bounded, resumable Dream loop state each turn.
        self._dream_continuations = 0
        self._dream_stall = 0
        self._dream_last_state = None
        self._dream_mtime_snapshot = None
        self._ledger = None
        self._tests_cache = None
        self._fakes_cache = None

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
            # Persistent task ledger — resume a crashed job (same goal) or build
            # a fresh milestone list. This is the objective record of what work
            # is promised vs. delivered; the loop won't finalize while items are
            # pending. Fully wrapped so an offline/failed decompose never breaks
            # the turn.
            try:
                from .core import ledger
                self._ledger = ledger.resume_or_create(
                    self.cfg.workdir, user_input, self.cfg)
                self._append_history(
                    "user",
                    "[DREAM LEDGER] Mark each milestone done via the "
                    "ledger_update tool ONLY when its REAL code exists and its "
                    "tests pass. Pending milestones trigger bounded continuation:\n"
                    + ledger.pending_summary(self._ledger, limit=40))
            except Exception:
                self._ledger = None
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
        # Dream mode: honor the profile budget while enforcing the global hard cap,
        # keeping each run resumable and bounded.
        if getattr(self.effort, "dream_mode", False):
            # The profile may advertise a large theoretical budget, but the
            # per-process hard cap must always win to keep execution resumable.
            max_steps = min(max(max_steps, 1), DREAM_HARD_CAP)

        for step in range(max_steps):
            with self._telemetry_lock:
                self.current_step = step + 1
            if self.cancel_event.is_set():
                self._finish_telemetry(started_at)
                return "Stopped by user (Esc)."

            # Streaming or non-streaming LLM call
            if on_text is not None:
                def _on_stream_delta(delta: str) -> None:
                    if delta:
                        with self._telemetry_lock:
                            self._live_output_chars += len(delta)
                    on_text(delta)
                msg = stream_chat(self.cfg, self.history, SCHEMAS, _on_stream_delta,
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
                # DREAM MODE: don't finalize until the goal is verifiably
                # complete, or a hard cap/stall/provider blocker requires a report.
                if (getattr(self.effort, "dream_mode", False)
                        and not self.cancel_event.is_set()):
                    done, reason = self._dream_completion_check()
                    if (not done
                            and self._dream_continuations < DREAM_CONTINUATION_CAP):
                        self._dream_continuations += 1
                        self._append_history("user",
                                             DREAM_CONTINUATION_PROMPT + reason)
                        continue
                answer = self._finalize(answer)
                self._finish_telemetry(started_at)
                return answer

            # Execute tool calls
            for call in tool_calls:
                if self.cancel_event.is_set():
                    self._finish_telemetry(started_at)
                    return "Stopped by user (Esc)."
                result = self._execute_tool(call)
                self._tool_call_count += 1
                with self._telemetry_lock:
                    self.total_tool_calls += 1
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
                # A new edit invalidates any prior clean verification pass, so
                # the two required passes must be genuinely consecutive.
                if getattr(self.effort, "dream_mode", False):
                    try:
                        from .core import ledger
                        ledger.reset_verify_passes(self.cfg.workdir)
                    except Exception:
                        pass

            # Self-healing: if agent detected a failure, retry
            if getattr(self.effort, "self_healing", False):
                self._self_heal_check()

        self._finish_telemetry(started_at)
        return "Max steps reached."

    def _finish_telemetry(self, started_at: float) -> None:
        with self._telemetry_lock:
            self.last_latency_ms = max(0.0, (time.monotonic() - started_at) * 1000.0)
            self.current_step = 0

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

    # --- bounded Dream completion check ---
    def _workdir_mtime_state(self) -> tuple:
        """Cheap fingerprint of the tree so we can detect 'nothing changed'.

        Tracks ALL text file types (not just .py) so changes to .json, .md,
        .txt, .yaml, .toml etc. are also detected — previously agent could
        write non-Python files and the loop would wrongly declare 'no changes'.
        """
        import os
        _TRACK_EXTS = {
            ".py", ".js", ".ts", ".json", ".yaml", ".yml",
            ".toml", ".md", ".txt", ".html", ".css", ".sh",
            ".go", ".rs", ".java", ".c", ".cpp", ".rb",
        }
        wd = self.cfg.workdir
        stamps: list[tuple] = []
        for dirpath, dirnames, filenames in os.walk(wd):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d not in
                           ("__pycache__", "node_modules", ".git",
                            ".venv", "venv", ".ruff_cache")]
            for f in filenames:
                if not any(f.endswith(ext) for ext in _TRACK_EXTS):
                    continue
                fp = os.path.join(dirpath, f)
                try:
                    stamps.append((fp, os.path.getmtime(fp)))
                except OSError:
                    continue
        return tuple(sorted(stamps))

    def _dream_completion_check(self) -> tuple[bool, str]:
        """Decide if the dream goal is verifiably done.

        Enterprise-scale: works in bounded batches for large projects.
        It stops when the goal is verified, cancelled, blocked, stalled, or capped:
          1. Zero blocking fake/stub findings
          2. Zero recent tool errors
          3. Tests pass (if any exist)
          4. No file changes in last check (nothing left to do)

        Stall guard: only triggers after DREAM_STALL_LIMIT consecutive checks
        with ZERO tool activity AND identical measurable state.
        """
        # 1. mtime check — if files changed, progress was made; reset the stall guard.
        mtime_state = self._workdir_mtime_state()
        files_changed = (
            self._dream_mtime_snapshot is not None
            and mtime_state != self._dream_mtime_snapshot
        )
        if files_changed:
            # Agent made progress — reset stall counter
            self._dream_stall = 0
            self._dream_last_state = None
        self._dream_mtime_snapshot = mtime_state

        # 2. Count recent tool calls — active work resets the stall guard.
        recent_tool_calls = sum(
            1 for m in self.history[-20:]
            if m.get("role") == "tool"
        )
        if recent_tool_calls >= 3:
            # Agent is actively working — reset stall, don't check completion yet
            self._dream_stall = 0
            return False, f"agent actively working ({recent_tool_calls} recent tool calls)"

        # 3. Fake/simulated code — blocking findings must be zero.
        blocking_fakes = self._count_blocking_fakes()

        # 4. Recent tool errors.
        error_count = sum(
            1 for m in self.history[-12:]
            if m.get("role") == "tool" and (m.get("content") or "").startswith("Error:")
        )

        # 5. Tests (if a test command exists).
        tests_failing = self._tests_failing()

        heuristic_done = (blocking_fakes == 0) and (error_count == 0) and (not tests_failing)

        # 6. Ledger gate — every promised milestone must be marked done. This is
        # what stops the model from "quitting early" on a 40K-file job: the
        # ledger is the objective record of promised-vs-delivered work.
        ledger_data = None
        ledger_clear = True
        if self._ledger is not None:
            try:
                from .core import ledger
                ledger_data = ledger.load(self.cfg.workdir) or self._ledger
                ledger_clear = ledger.is_complete(ledger_data)
            except Exception:
                ledger_clear = True

        # Stall detection: only stop if state is IDENTICAL for DREAM_STALL_LIMIT
        # consecutive checks AND agent has not been calling tools.
        pending = (0 if ledger_data is None
                   else self._ledger_pending(ledger_data))
        state = (blocking_fakes, tests_failing, error_count, recent_tool_calls, pending)
        if state == self._dream_last_state:
            self._dream_stall += 1
        else:
            self._dream_stall = 0
            self._dream_last_state = state

        # Real completion requires ALL THREE: no blocking issues, ledger clear,
        # and TWO independent verification passes clean.
        if heuristic_done and ledger_clear:
            both_ok, verify_errors = self._dream_double_verify()
            if both_ok:
                return True, ("(verified 2x: ledger complete, no fake code, "
                              "no errors, tests pass)")
            # Double-verify caught something the heuristic missed — feed the
            # concrete issues back for self-heal and keep going.
            self._append_history(
                "user",
                "[DREAM DOUBLE-VERIFY FAILED] The goal is NOT done. Fix these "
                "concrete issues with real code, then continue — do NOT stop:\n"
                + verify_errors)
            return False, "double-verify failed: " + verify_errors[:200]

        # Stall guard: bounded escape hatch so the loop can never run forever.
        if self._dream_stall >= DREAM_STALL_LIMIT:
            return True, (
                f"(no measurable progress after {DREAM_STALL_LIMIT} checks — "
                f"fakes={blocking_fakes} errors={error_count} "
                f"tests_failing={tests_failing} pending={pending})"
            )

        reasons = []
        if not ledger_clear and ledger_data is not None:
            from .core import ledger
            reasons.append(ledger.pending_summary(ledger_data, limit=8))
        if blocking_fakes:
            reasons.append(f"{blocking_fakes} fake/stub finding(s) to rewrite")
        if tests_failing:
            reasons.append("tests are failing")
        if error_count:
            reasons.append(f"{error_count} recent tool error(s)")
        return False, "; ".join(reasons) or "goal not verified yet"

    def _ledger_pending(self, ledger_data: dict) -> int:
        """Pending milestone count (thin wrapper, import-safe)."""
        try:
            from .core import ledger
            return ledger.pending_count(ledger_data)
        except Exception:
            return 0

    def _dream_double_verify(self) -> tuple[bool, str]:
        """Run the verification plane TWICE, independently. Both must be clean.

        Between passes we drop the fake/test caches so the second pass genuinely
        re-walks the tree instead of reusing pass-1 results. A clean double pass
        bumps the ledger's verify_passes counter; any failure resets it, so the
        two clean passes are always consecutive.
        """
        from .core import dream, ledger

        def _one_pass() -> tuple[bool, str]:
            try:
                report = dream.verification_plane(self.cfg, self.history)
            except Exception as e:
                return False, f"verification_plane error: {e}"
            problems = self._parse_verification(report)
            return (not problems), "; ".join(problems)

        ok1, err1 = _one_pass()
        if not ok1:
            try:
                ledger.reset_verify_passes(self.cfg.workdir)
            except Exception:
                pass
            return False, "pass-1: " + err1

        # Force the second pass to be independent (no cached fake/test results).
        self._fakes_cache = None
        self._tests_cache = None

        ok2, err2 = _one_pass()
        if not ok2:
            try:
                ledger.reset_verify_passes(self.cfg.workdir)
            except Exception:
                pass
            return False, "pass-2: " + err2

        try:
            ledger.bump_verify_passes(self.cfg.workdir)
        except Exception:
            pass
        return True, ""

    def _parse_verification(self, report: str) -> list[str]:
        """Extract blocking problems from a verification_plane report.

        Pure string/heuristic parse — no LLM. Fake findings, failing tests, and
        syntax errors block; secret-scan hits are advisory (avoid false stops).
        """
        import re
        problems: list[str] = []
        text = report or ""

        m = re.search(r"Fake/stub findings:\s*(\d+)", text)
        if m and int(m.group(1)) > 0:
            problems.append(f"{m.group(1)} fake/stub finding(s)")

        if "SyntaxError" in text:
            problems.append("syntax error(s) present")

        # Independent test run (cache was just cleared by the caller between passes).
        if self._tests_failing():
            problems.append("tests are failing")

        return problems

    def _count_blocking_fakes(self) -> int:
        """Run the fake-code engine and parse its machine-readable count.

        Cached per mtime snapshot so repeated completion checks in the same
        loop iteration don't re-walk the entire codebase (was the #1 cause
        of dream mode slowness).
        """
        import re
        import time as _time
        mtime_key = self._dream_mtime_snapshot
        cached = getattr(self, "_fakes_cache", None)
        # Cache hit: same mtime snapshot AND within TTL
        if (cached is not None
                and cached[0] == mtime_key
                and (_time.monotonic() - cached[2]) < DREAM_FAKE_CACHE_TTL):
            return cached[1]
        try:
            from .core.dream import _fake_code_detection
            out = _fake_code_detection(self.cfg.workdir)
        except Exception:
            return 0
        m = re.search(r"Fake/stub findings:\s*(\d+)", out)
        count = int(m.group(1)) if m else 0
        self._fakes_cache = (mtime_key, count, _time.monotonic())
        return count

    def _tests_failing(self) -> bool:
        """True only if a test command exists AND it reports failures.

        Caches the result per mtime snapshot to avoid re-running tests
        on every dream completion check (expensive).
        """
        cmd = self._detect_test_command()
        if not cmd:
            return False  # no tests → don't block completion
        # Use mtime snapshot as cache key to avoid redundant test runs
        mtime_key = self._dream_mtime_snapshot
        cached = getattr(self, "_tests_cache", None)
        if cached is not None and cached[0] == mtime_key:
            return cached[1]
        try:
            out = REGISTRY["run_shell"].run(self.cfg.workdir, command=cmd,
                                            timeout_seconds=90)
        except Exception:
            return False
        result = any(w in out.lower() for w in ("fail", "error", "traceback"))
        self._tests_cache = (mtime_key, result)
        return result

    # --- effort preflight (before acting) ---
    def _effort_preflight(self, user_input: str) -> None:
        e = self.effort
        if not e.enterprise_preflight:
            return
        import concurrent.futures
        blocks: list[str] = []
        lock = __import__("threading").Lock()

        def _safe_append(label: str, fn):
            try:
                out = fn()
                if out:
                    with lock:
                        blocks.append(f"## {label}\n{str(out)[:1500]}")
            except Exception:
                pass

        # Checkpoint must run first (sequential — writes to disk)
        if e.auto_checkpoint:
            try:
                from .core import checkpoint
                blocks.append(checkpoint.create(self.cfg.workdir))
            except Exception:
                pass

        # All analysis tasks run in parallel
        parallel_tasks: list[tuple[str, object]] = []
        if e.run_metrics:
            parallel_tasks.append(
                ("metrics", lambda: REGISTRY["code_metrics"].run(self.cfg.workdir)))
        if e.run_security:
            parallel_tasks.append(
                ("secret_scan", lambda: REGISTRY["secret_scan"].run(self.cfg.workdir)))
        if e.deep_research:
            parallel_tasks.append(
                ("deps", lambda: REGISTRY["deps"].run(self.cfg.workdir)))

        if parallel_tasks:
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=len(parallel_tasks)) as ex:
                futs = {ex.submit(fn): label for label, fn in parallel_tasks}
                for fut in concurrent.futures.as_completed(futs, timeout=60):
                    label = futs[fut]
                    try:
                        out = fut.result(timeout=30)
                        if out:
                            blocks.append(f"## {label}\n{str(out)[:1500]}")
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
                if "No secrets" not in out and "no secrets" not in out.lower():
                    findings.append("SECURITY:\n" + out[:1500])
            except Exception:
                pass
        if e.run_quality:
            import os
            # Lint ALL Python files, not just the first one
            lint_issues: list[str] = []
            try:
                for f in sorted(os.listdir(self.cfg.workdir)):
                    if not f.endswith(".py"):
                        continue
                    try:
                        out = REGISTRY["lint"].run(self.cfg.workdir, path=f)
                        if "no issues" not in out.lower() and "ok" not in out.lower() and "SyntaxError" in out:
                            lint_issues.append(out[:400])
                    except Exception:
                        pass
                # Also lint zedpy/ subdirectory if present
                zedpy_dir = os.path.join(self.cfg.workdir, "zedpy")
                if os.path.isdir(zedpy_dir):
                    for root_dir, _, files in os.walk(zedpy_dir):
                        for f in files:
                            if not f.endswith(".py"):
                                continue
                            rel = os.path.relpath(os.path.join(root_dir, f), self.cfg.workdir)
                            try:
                                out = REGISTRY["lint"].run(self.cfg.workdir, path=rel)
                                if "SyntaxError" in out:
                                    lint_issues.append(out[:400])
                            except Exception:
                                pass
            except Exception:
                pass
            if lint_issues:
                findings.append("LINT ERRORS:\n" + "\n".join(lint_issues[:5]))
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
        with self._telemetry_lock:
            self.total_input_tokens += int(u.get("prompt_tokens", 0) or 0)
            self.total_output_tokens += int(u.get("completion_tokens", 0) or 0)

    def stats(self) -> dict:
        with self._telemetry_lock:
            live_output_tokens = max(0, self._live_output_chars // 4)
            return {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "live_input_tokens": self._live_input_estimate,
                "live_output_tokens": live_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "messages": len(self.history),
                "requests": self.total_requests,
                "tool_calls": self.total_tool_calls,
                "current_step": self.current_step,
                "latency_ms": round(self.last_latency_ms, 1),
            }
