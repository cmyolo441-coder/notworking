"""BITTU — Grok CLI-style terminal UI (Textual).

Recreates the reference screenshot: centered brand constellation, an amber
mode-labelled prompt box ("Plan / What are we building?"), a status line
("BITTU Code Fast  99% 254K  shift+enter new line  tab modes"), and a footer
with the cwd (left) and version (right). Slash commands work like Claude Code.
"""
from __future__ import annotations

import os
import threading
import time

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.events import Paste
from textual.widgets import Input, Static

from .. import commands as cmds
from ..agent import Agent
from ..config import Config
from ..core.session import Session
from ..llm import LLMError
from .constellation import constellation

BRAND = "BITTU"
VERSION = "v2.0.0"
MODES = ["Plan", "Build", "Chat"]
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class PasteInput(Input):
    """Input subclass that supports full clipboard paste without auto-send.

    Default Textual Input._on_paste only takes splitlines()[0] (first line),
    losing multi-line paste.  Our override inserts the FULL clipboard content,
    replacing newlines with spaces so the single-line Input stays clean.
    Pasted text NEVER auto-sends — user must press Enter explicitly.
    """

    def action_paste(self) -> None:
        """Ctrl+V paste — full clipboard content, newline→space, no auto-send."""
        clipboard = self.app.clipboard or ""
        if not clipboard:
            return
        # Newlines ko space se replace karo (Input single-line hai).
        text = clipboard.replace("\r", "").replace("\n", " ")
        start, end = self.selection
        self.replace(text, start, end)

    def _on_paste(self, event: Paste) -> None:
        """Bracketed paste — full content insert, no auto-send."""
        if event.text:
            text = event.text.replace("\r", "").replace("\n", " ")
            selection = self.selection
            if selection.is_empty:
                self.insert_text_at_cursor(text)
            else:
                self.replace(text, *selection)
        event.stop()


class BittuApp(App):
    """The main Textual application."""

    CSS = """
    Screen {
        background: #080d18;
        color: #dce7f5;
        layout: vertical;
    }

    #topbar {
        height: 2;
        background: #0f1a2c;
        border-bottom: solid #1e3854;
        padding: 0 3;
        color: #8ea8c6;
        content-align: left middle;
    }
    #topbar-title { color: #f2b35a; text-style: bold; }
    #topbar-hint { color: #7189a7; padding: 0 0 0 2; }

    #hero {
        height: 1fr;
        align: center middle;
        content-align: center middle;
        background: #080d18;
    }
    #logo { width: auto; height: auto; content-align: center middle; color: #f2b35a; }
    #tagline { width: auto; height: 1; color: #6d87a6; content-align: center middle; }

    #transcript {
        height: 1fr;
        background: #0b1322;
        border: round #1e3854;
        margin: 1 3 0 3;
        padding: 1 2;
        display: none;
        overflow-y: scroll;
        scrollbar-size-vertical: 1;
        scrollbar-color: #f2b35a;
        scrollbar-color-hover: #ffd07a;
        scrollbar-background: #111d31;
    }
    #transcript > .msg {
        height: auto;
        width: 100%;
        margin: 0 0 1 0;
        padding: 0 1;
    }

    #promptbox {
        height: auto;
        background: #101d31;
        border: round #2b5273;
        margin: 1 3 0 3;
        padding: 1 2;
    }
    #promptrow { height: auto; layout: horizontal; }
    #modelabel {
        width: auto;
        color: #f2b35a;
        text-style: bold;
        padding: 0 2 0 0;
    }
    #prompt {
        width: 1fr;
        background: #101d31;
        border: none;
        color: #f2f6fb;
        padding: 0;
    }
    #prompt:focus { border: none; }
    #prompt.-disabled { color: #60758f; }

    #status {
        height: 1;
        background: #0f1a2c;
        margin: 0 3;
        padding: 0 2;
        color: #7892b1;
    }

    #palette {
        height: auto;
        max-height: 22;
        background: #101d31;
        border: round #2b5273;
        margin: 0 3;
        padding: 1 2;
        color: #aec1d7;
        display: none;
    }

    #telemetry {
        height: 1;
        background: #0b1728;
        margin: 0 3;
        padding: 0 2;
        color: #7892b1;
        border-top: solid #17334f;
    }

    #footer {
        height: 1;
        layout: horizontal;
        padding: 0 3;
        color: #526984;
    }
    #cwd { width: 1fr; }
    #version { width: auto; content-align: right middle; }

    """

    BINDINGS = [
        Binding("tab", "cycle_mode", "modes", show=False),
        Binding("ctrl+c", "stop", "stop", show=False),
        Binding("ctrl+space", "focus_prompt", "focus prompt", show=False),
        Binding("ctrl+l", "clear_convo", "clear", show=False),
        Binding("escape", "stop", "stop", show=False),
        Binding("pageup", "palette_up", "prev command", show=False),
        Binding("pagedown", "palette_down", "next command", show=False),
        # Model selector navigation
        Binding("ctrl+pageup", "model_selector_up", "prev model", show=False),
        Binding("ctrl+pagedown", "model_selector_down", "next model", show=False),
        Binding("ctrl+enter", "model_selector_select", "select model", show=False),
        # Transcript scrolling
        Binding("ctrl+k", "scroll_up", "scroll up", show=False),
        Binding("ctrl+j", "scroll_down", "scroll down", show=False),
        Binding("ctrl+u", "scroll_page_up", "page up", show=False),
        Binding("ctrl+d", "scroll_page_down", "page down", show=False),
        Binding("ctrl+g", "scroll_top", "top", show=False),
        Binding("ctrl+b", "scroll_bottom", "bottom", show=False),
        Binding("ctrl+up", "scroll_up", "scroll up", show=False),
        Binding("ctrl+down", "scroll_down", "scroll down", show=False),
        Binding("ctrl+home", "scroll_top", "top", show=False),
        Binding("ctrl+end", "scroll_bottom", "bottom", show=False),
        Binding("shift+up", "scroll_up", "scroll up", show=False),
        Binding("shift+down", "scroll_down", "scroll down", show=False),
        Binding("shift+pageup", "scroll_page_up", "page up", show=False),
        Binding("shift+pagedown", "scroll_page_down", "page down", show=False),
    ]

    # Mouse OFF rakhte hain taaki terminal ka native text-select/copy chale.
    # (Textual by default mouse capture karta hai jo copy rok deta hai.)
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg
        self.agent = Agent(cfg)
        self.mode_index = 0
        self.busy = False
        self.session = Session.new(cfg.model, cfg.workdir)  # F1
        # Slash-palette navigation state.
        self._palette_matches: list = []
        self._palette_index: int = 0
        self._palette_query: str = ""
        # Model selector state
        self._model_selector_active: bool = False
        self._model_selector_index: int = 0
        self._model_selector_items: list = []
        # #17 — command history
        self.cmd_history: list[str] = []
        # Streaming: persistent Text + delta buffer for batched writes.
        self._stream_text: Text | None = None
        self._stream_widget: Static | None = None
        self._stream_started: bool = False
        self._stream_delta_buf: str = ""
        self._stream_last_flush: float = 0.0
        # Working spinner state.
        self._spin_idx: int = 0
        self._spin_timer = None
        self._work_start: float = 0.0
        self._worker_thread: threading.Thread | None = None
        self._closing: bool = False
        self._web_source_count: int = 0

    # --- layout -----------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Container(id="topbar"):
            yield Static(f"{BRAND}  /  autonomous coding workspace", id="topbar-title")
            yield Static("tab modes · / commands · esc stop", id="topbar-hint")
        with Container(id="hero"):
            yield Static(self._logo(), id="logo")
            yield Static("Build deliberately. Inspect everything. Ship real code.", id="tagline")
        yield VerticalScroll(id="transcript")
        yield Static("", id="palette")
        with Vertical(id="promptbox"):
            with Container(id="promptrow"):
                yield Static(self._mode_name(), id="modelabel")
                yield PasteInput(placeholder="What are we building?", id="prompt")
        yield Static(self._status_text(), id="status")
        yield Static(self._telemetry_text(), id="telemetry")
        with Container(id="footer"):
            yield Static(self._cwd_text(), id="cwd")
            yield Static("esc stop · enter send · ^k/^j scroll · " + VERSION, id="version")

    def _wire_agent_callbacks(self) -> None:
        """Attach callbacks after every Agent rebuild (model/workdir/reset/resume)."""
        self.agent._approve_cb = self._approve_tool
        self.agent._tool_cb = self._show_tool_call
        self.agent._tool_result_cb = self._show_tool_result

    def on_mount(self) -> None:
        self._closing = False
        self.query_one("#prompt", PasteInput).focus()
        self._spin_timer = self.set_interval(0.12, self._tick_spinner)
        self._wire_agent_callbacks()

    def on_unmount(self) -> None:
        """Stop background work before Textual releases its event loop."""
        self._closing = True
        self.agent.cancel_event.set()
        thread = self._worker_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._worker_thread = None

    # --- rendering helpers ------------------------------------------------
    def _logo(self) -> Text:
        return constellation(BRAND, width=58, height=9)

    def _mode_name(self) -> str:
        return MODES[self.mode_index]

    def _tick_spinner(self) -> None:
        """Advance the spinner frame + refresh status bar when busy."""
        if self.busy:
            self._spin_idx = (self._spin_idx + 1) % len(SPINNER)
            self.refresh_status()

    def _spin_char(self) -> str:
        return SPINNER[self._spin_idx] if self.busy else " "

    def _status_text(self) -> Text:
        # F7 — live token usage.
        stats = self.agent.stats() if hasattr(self, "agent") else {"input_tokens": 0, "output_tokens": 0}
        tok = stats["input_tokens"] + stats["output_tokens"]
        tok_str = f"{tok/1000:.1f}K" if tok >= 1000 else str(tok)
        eff = self.agent.effort if hasattr(self, "agent") else None
        eff_label = eff.label if eff else "Normal"
        eff_style = "#e8a13a bold" if eff and eff.name != "normal" else "#999999"
        t = Text()
        # Working indicator: animated spinner + elapsed seconds jab AI busy ho.
        if self.busy:
            elapsed = time.monotonic() - self._work_start if self._work_start else 0.0
            t.append(f" {self._spin_char()} ", style="#e8a13a bold")
            t.append(f"working… {elapsed:4.1f}s  ", style="#e8a13a bold")
        t.append(f"{BRAND} ", style="#b3b3b3")
        t.append(f"[{eff_label}]", style=eff_style)
        # Show model name in Dream Mode
        if eff and eff.name == "dream":
            model_short = self.cfg.model.split("/")[-1] if "/" in self.cfg.model else self.cfg.model
            t.append(f" ({model_short})", style="#00ff00 bold")
        t.append(f" {tok_str} tokens", style="#808080")
        t.append("        ")
        t.append("enter ", style="#b3b3b3")
        t.append("send", style="#808080")
        t.append("    ")
        t.append("tab ", style="#b3b3b3")
        t.append("modes", style="#808080")
        if self.cfg.auto_approve:
            t.append("    ")
            t.append("YOLO", style="#e8a13a bold")
        return t

    def _telemetry_text(self) -> Text:
        stats = self.agent.stats() if hasattr(self, "agent") else {}
        exact_in = int(stats.get("input_tokens", 0) or 0)
        exact_out = int(stats.get("output_tokens", 0) or 0)
        live_in = int(stats.get("live_input_tokens", 0) or 0)
        live_out = int(stats.get("live_output_tokens", 0) or 0)
        requests = int(stats.get("requests", 0) or 0)
        tools = int(stats.get("tool_calls", 0) or 0)
        step = int(stats.get("current_step", 0) or 0)
        latency = float(stats.get("latency_ms", 0.0) or 0.0)
        t = Text("  TELEMETRY  ", style="#f2b35a bold")
        t.append(f"in {exact_in:,}  out {exact_out:,}", style="#c2d4e8")
        if self.busy:
            t.append(f"  live~in {live_in:,}  live~out {live_out:,}", style="#6fe3b1")
        t.append(f"  req {requests}  tools {tools}", style="#7892b1")
        if self.busy and step:
            t.append(f"  step {step}", style="#e8a13a")
        elif latency:
            t.append(f"  last {latency/1000:.2f}s", style="#7892b1")
        if self._web_source_count:
            t.append(f"  web {self._web_source_count} refs", style="#78c8ff")
        return t

    def _cwd_text(self) -> str:
        home = os.path.expanduser("~")
        p = self.cfg.workdir
        if p.startswith(home):
            p = "~" + p[len(home):]
        return p

    def refresh_status(self) -> None:
        self.query_one("#status", Static).update(self._status_text())
        self.query_one("#telemetry", Static).update(self._telemetry_text())
        mode = self._mode_name()
        self.query_one("#modelabel", Static).update(mode)
        self.query_one("#prompt", PasteInput).placeholder = {
            "Plan": "What are we planning?",
            "Build": "What are we building?",
            "Chat": "Ask BITTU anything…",
        }.get(mode, "What are we building?")
        self.query_one("#cwd", Static).update(self._cwd_text())

    # --- agent callbacks (TUI mode) --------------------------------------
    def _approve_tool(self, name: str, args: dict) -> bool:
        """Approve read-only tools automatically; require explicit YOLO for mutations.

        The old UI silently approved every write/shell/HTTP operation, which made
        the visible approval flag meaningless. A non-YOLO TUI now remains safe
        by default and explains the exact opt-in needed in the transcript.
        """
        read_only = {
            "read_file", "list_dir", "grep", "find_files", "tree", "code_metrics",
            "fuzzy_find", "lint", "deps", "secret_scan", "todo_scan", "fake_scan",
            "show_diff", "data_tool",
        }
        git_action = str(args.get("action", "")).lower()
        git_args = str(args.get("args", "")).strip()
        git_read_only = name == "git" and (
            git_action in {"status", "diff", "log", "show"}
            or (git_action == "branch" and not any(flag in git_args.split() for flag in {"-d", "-D", "--delete", "--move", "-m", "-M", "--edit-description"}))
        )
        if name in read_only or git_read_only or self.cfg.auto_approve or self.cfg.yolo_mode:
            return True
        self.call_from_thread(
            self.log_system,
            f"Approval required for {name}. Set ZEDPY_AUTO_APPROVE=true to enable mutating tools.",
        )
        return False

    def _show_tool_call(self, text: str) -> None:
        """Agent jab tool chalaye to transcript me dikhao."""
        self.call_from_thread(self.log_tool, text)

    def _show_tool_result(self, name: str, result: str) -> None:
        """Tool execution ke baad result transcript me dikhao (truncated)."""
        # Large results (read_file output) ko truncate karo taaki UI na toote.
        if len(result) > 1200:
            shown = result[:1200] + f"\n…[{len(result) - 1200} chars truncated]"
        else:
            shown = result
        self.call_from_thread(self.log_tool_result, name, shown)

    def log_tool_result(self, name: str, result: str) -> None:
        if name == "web_search":
            import re
            self._web_source_count = max(self._web_source_count, len(re.findall(r"^\[\d+\] ", result, re.MULTILINE)))
            self.refresh_status()
        self._add_msg(Text(f"  ✓ {name} →", style="#e8a13a").append(
            f" {result[:300]}" if len(result) > 300 else f" {result}", style="#808080"))

    # --- transcript -------------------------------------------------------
    def _reveal_transcript(self) -> None:
        """Hide the hero logo, show the scrolling transcript (after 1st msg)."""
        self.query_one("#hero").styles.display = "none"
        self.query_one("#transcript").styles.display = "block"

    def _transcript(self) -> VerticalScroll:
        return self.query_one("#transcript", VerticalScroll)

    def _at_bottom(self) -> bool:
        """User bottom ke paas hai? (tabhi auto-follow karo)."""
        ts = self._transcript()
        return ts.scroll_offset.y >= ts.max_scroll_y - 2

    def _add_msg(self, renderable) -> Static:
        """Ek naya transcript line/message widget mount karo.

        Agar user upar scroll karke purana message padh raha hai to niche
        auto-scroll NAHI karte — position preserve hoti hai. Bottom par ho
        to hi naya content follow hota hai.
        """
        self._reveal_transcript()
        follow = self._at_bottom()
        w = Static(renderable, classes="msg")
        self._transcript().mount(w)
        if follow:
            self.call_after_refresh(self._scroll_end)
        return w

    def _scroll_end(self) -> None:
        self._transcript().scroll_end(animate=False)

    def log_user(self, text: str) -> None:
        self._add_msg(Text(f"› {text}", style="bold #d0d0d0"))

    def log_bittu(self, text: str) -> None:
        self._add_msg(Text(f"{BRAND}: ", style="#e8a13a bold").append(text, style="#d9d9d9"))

    def log_tool(self, text: str) -> None:
        self._add_msg(Text(f"  ⚙ {text}", style="#808080"))

    def log_system(self, text: str) -> None:
        self._add_msg(Text(text, style="#9e9e9e"))

    # --- scroll actions (work while Input is focused) ---------------------
    def _scroll_by(self, dy: int) -> None:
        """Transcript ko dy lines scroll karo (guarded)."""
        try:
            ts = self._transcript()
        except Exception:
            return
        if ts.styles.display == "none":
            return
        ts.scroll_relative(y=dy, animate=False)

    def action_scroll_up(self) -> None:
        self._scroll_by(-3)

    def action_scroll_down(self) -> None:
        self._scroll_by(3)

    def action_scroll_page_up(self) -> None:
        try:
            self._transcript().scroll_page_up(animate=False)
        except Exception:
            pass

    def action_scroll_page_down(self) -> None:
        try:
            self._transcript().scroll_page_down(animate=False)
        except Exception:
            pass

    def action_scroll_top(self) -> None:
        try:
            self._transcript().scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_bottom(self) -> None:
        try:
            self._transcript().scroll_end(animate=False)
        except Exception:
            pass

    # --- mouse wheel: transcript scroll no matter where cursor is ---------
    def on_mouse_scroll_down(self, event) -> None:
        self._scroll_by(3)
        event.stop()

    def on_mouse_scroll_up(self, event) -> None:
        self._scroll_by(-3)
        event.stop()

    # --- slash-command palette (PgUp/PgDown navigable) --------------------
    def _update_palette(self, value: str) -> None:
        """Update the compact command palette from the current prompt text.

        Only a command prefix is considered a palette query.  Once an argument
        is present, normal command dispatch owns the input and the dropdown is
        hidden.  Matching is deliberately palette-scoped: real tools such as
        web search, fetch, telemetry, indexing, and scans remain available when
        explicitly typed but are not presented as the primary UX.
        """
        if self._model_selector_active:
            return
        palette = self.query_one("#palette", Static)
        if value.startswith("/") and " " not in value:
            self._palette_query = value
            matches = cmds.match(value, palette=True)
            self._palette_matches = matches
            if self._palette_index >= len(matches):
                self._palette_index = 0
            self._render_palette()
            palette.styles.display = "block"
            return
        self._palette_query = ""
        self._palette_matches = []
        self._palette_index = 0
        palette.styles.display = "none"

    def _render_palette(self) -> None:
        """Draw grouped rows, live query state, and the current selection."""
        palette = self.query_one("#palette", Static)
        t = Text()
        query = self._palette_query or "/"
        t.append("  COMMAND PALETTE  ", style="#e8a13a bold")
        t.append(f"{query}\n", style="#c2d4e8 bold")
        t.append("  PgUp/PgDown move · Enter/Tab choose · Esc close\n", style="#7189a7")

        if not self._palette_matches:
            t.append("\n  No useful controls match this prefix.\n", style="#9e9e9e")
            t.append("  Type /help for the full explicit command registry.\n", style="#7189a7")
            palette.update(t)
            return

        current_category = None
        for i, command in enumerate(self._palette_matches):
            category = getattr(command, "category", "GENERAL")
            if category != current_category:
                if current_category is not None:
                    t.append("\n")
                t.append(f"  {category}\n", style="#78c8ff bold")
                current_category = category
            selected = (i == self._palette_index)
            if selected:
                t.append("  ▶ ", style="#e8a13a bold")
                t.append(f"{command.name:<18}", style="black on #e8a13a bold")
                t.append(f" {command.summary}\n", style="white")
            else:
                t.append("    ")
                t.append(f"{command.name:<18}", style="#e8a13a")
                t.append(f" {command.summary}\n", style="#9e9e9e")
        palette.update(t)

    def action_palette_up(self) -> None:
        if self._palette_matches:
            self._palette_index = (self._palette_index - 1) % len(self._palette_matches)
            self._render_palette()

    def action_palette_down(self) -> None:
        if self._palette_matches:
            self._palette_index = (self._palette_index + 1) % len(self._palette_matches)
            self._render_palette()

    def _accept_palette(self) -> bool:
        """If the palette is open, fill the input with the selected command.

        Returns True if a selection was applied (so Enter shouldn't submit yet).
        """
        if self._palette_matches:
            chosen = self._palette_matches[self._palette_index]
            inp = self.query_one("#prompt", PasteInput)
            inp.value = chosen.name + " "
            inp.cursor_position = len(inp.value)
            self._palette_matches = []
            self._palette_query = ""
            self.query_one("#palette", Static).styles.display = "none"
            return True
        return False

    # --- Model Selector (PgUp/PgDown navigable) ---------------------------
    def _show_model_selector(self) -> None:
        """Show all available models in a navigable list."""
        from ..config import MODEL_PROFILES

        # Sort models: dream models first when dream mode is active
        items = list(MODEL_PROFILES.items())
        if hasattr(self, 'agent') and self.agent.effort and self.agent.effort.name == "dream":
            # Put dream models at the top
            dream_items = [(n, p) for n, p in items if 'dream' in n.lower()]
            other_items = [(n, p) for n, p in items if 'dream' not in n.lower()]
            items = dream_items + other_items

        self._model_selector_items = items
        self._model_selector_index = 0

        # Find current model in list
        for i, (name, profile) in enumerate(self._model_selector_items):
            if profile.model == self.cfg.model:
                self._model_selector_index = i
                break

        self._model_selector_active = True
        self._render_model_selector()

    def _render_model_selector(self) -> None:
        """Draw the model selector dropdown."""
        palette = self.query_one("#palette", Static)
        t = Text()
        t.append("═══ SELECT MODEL ═══\n", style="#e8a13a bold")
        t.append("(Ctrl+PgUp/PgDn navigate · Ctrl+Enter select · Esc cancel)\n\n", style="#595959")

        # Show dream mode indicator if active
        if hasattr(self, 'agent') and self.agent.effort and self.agent.effort.name == "dream":
            t.append("  🚀 DREAM MODE ACTIVE — Dream models shown first\n\n", style="#00ff00 bold")

        for i, (name, profile) in enumerate(self._model_selector_items):
            selected = (i == self._model_selector_index)
            current = (profile.model == self.cfg.model)

            # Provider indicator
            if "nvidia.com" in profile.base_url:
                provider = "NVIDIA"
                provider_style = "#76b900"  # NVIDIA green
            elif "cloudflare.com" in profile.base_url:
                provider = "CF"
                provider_style = "#f48120"  # Cloudflare orange
            else:
                provider = "OpenCode"
                provider_style = "#00d4aa"  # Teal

            # Dream mode indicator
            dream_indicator = " ⭐" if 'dream' in name.lower() else ""

            if selected:
                t.append("  ▶ ", style="#e8a13a bold")
                t.append(f"{name:<18}", style="black on #e8a13a bold")
                t.append(" ", style="")
                t.append(f"{provider:<10}", style=provider_style)
                t.append(f" {profile.model}{dream_indicator}", style="white bold")
                if current:
                    t.append(" ✓", style="#76b900 bold")
                t.append("\n", style="")
            else:
                t.append("    ")
                t.append(f"{name:<18}", style="#e8a13a")
                t.append(" ", style="")
                t.append(f"{provider:<10}", style=provider_style)
                t.append(f" {profile.model}", style="#9e9e9e")
                if current:
                    t.append(" ✓", style="#76b900")
                t.append("\n", style="")

        palette.update(t)
        palette.styles.display = "block"

    def action_model_selector_up(self) -> None:
        """Navigate up in model selector."""
        if self._model_selector_active and self._model_selector_items:
            self._model_selector_index = (self._model_selector_index - 1) % len(self._model_selector_items)
            self._render_model_selector()

    def action_model_selector_down(self) -> None:
        """Navigate down in model selector."""
        if self._model_selector_active and self._model_selector_items:
            self._model_selector_index = (self._model_selector_index + 1) % len(self._model_selector_items)
            self._render_model_selector()

    def action_model_selector_select(self) -> None:
        """Select the highlighted model."""
        if self._model_selector_active and self._model_selector_items:
            name, profile = self._model_selector_items[self._model_selector_index]
            self.cfg.apply_profile(name)
            self.agent = Agent(self.cfg)  # Rebuild agent with new config
            self._wire_agent_callbacks()
            self._model_selector_active = False
            self.query_one("#palette", Static).styles.display = "none"
            self.refresh_status()
            self.log_system(f"Model → {profile.model} ({name})")

    # --- Esc / Ctrl+C: stop a running agent turn ----------------------------
    def action_focus_prompt(self) -> None:
        """Return focus to the prompt from any transcript/palette state."""
        if self._closing:
            return
        self.query_one("#prompt", PasteInput).focus()

    def action_stop(self) -> None:
        if self.busy:
            self.agent.cancel_event.set()
            self.log_system("⏹ Stopping… (Esc/Ctrl+C)")
        else:
            # Model selector khula ho to band karo.
            if self._model_selector_active:
                self._model_selector_active = False
                self.query_one("#palette", Static).styles.display = "none"
                return
            # Palette khula ho to band karo.
            if self._palette_matches or self._palette_query:
                self._palette_matches = []
                self._palette_query = ""
                self.query_one("#palette", Static).styles.display = "none"

    # --- events -----------------------------------------------------------
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "prompt":
            self._update_palette(event.value)

    # --- Paste detection: long text paste pe auto-send mat karo ----------
    def on_paste(self, event: Paste) -> None:
        """Catch paste events globally — paste ko Input me bhejo, auto-send mat karo."""
        # PasteInput already handles this; yahan safety net hai.
        event.stop()

    def on_key(self, event) -> None:
        """Arrow / Tab navigation for the slash palette and model selector."""
        # Esc always works - stop agent or close selectors
        if event.key == "escape":
            self.action_stop()
            event.stop()
            event.prevent_default()
            return
        # Model selector navigation
        if self._model_selector_active:
            if event.key == "up":
                self.action_model_selector_up()
                event.stop()
                event.prevent_default()
            elif event.key == "down":
                self.action_model_selector_down()
                event.stop()
                event.prevent_default()
            elif event.key in ("enter", "ctrl+enter"):
                self.action_model_selector_select()
                event.stop()
                event.prevent_default()
            return
        # Slash palette navigation
        if not self._palette_matches:
            return
        if event.key == "up":
            self.action_palette_up()
            event.stop()
            event.prevent_default()
        elif event.key == "down":
            self.action_palette_down()
            event.stop()
            event.prevent_default()
        elif event.key == "tab":
            if self._accept_palette():
                event.stop()
                event.prevent_default()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Safety: busy hone pe submit ignore karo (paste-triggered submit bhi).
        if event.input.id != "prompt" or self.busy:
            return
        if self._accept_palette():
            return
        text = event.value.strip()
        event.input.value = ""
        # Don't hide palette if model selector is active
        if not self._model_selector_active:
            self.query_one("#palette", Static).styles.display = "none"
        if not text:
            return
        self.cmd_history.append(text)
        if text.startswith("/"):
            self._run_slash(text)
        else:
            self.log_user(text)
            self._run_agent_async(text)

    def _run_slash(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        name, arg = parts[0], (parts[1] if len(parts) > 1 else "")
        cmd = cmds.REGISTRY.get(name)
        if not cmd:
            self.log_system(f"Unknown command: {name}. Try /help")
            return
        self.log_user(text)
        result = cmd.handler(self, arg)
        if result:
            self.log_system(result)

    # --- agent execution (threaded so UI stays responsive) ----------------
    def _run_agent_async(self, text: str) -> None:
        if self._closing:
            return
        self.agent.cancel_event.clear()
        self.busy = True
        self._work_start = time.monotonic()
        # Web references are scoped to the current turn, not leaked from a prior goal.
        self._web_source_count = 0
        self.log_tool("thinking…")
        self._stream_started = False
        self._stream_text = None
        self._stream_widget = None
        self._stream_delta_buf = ""
        self._stream_last_flush = 0.0
        self.refresh_status()

        def on_text(delta: str):
            # Live streaming: text ko real-time transcript me likho.
            self.call_from_thread(self._stream_delta, delta)

        def worker():
            try:
                # Streaming ON (live token-by-token output).
                answer = self.agent.run(text, on_text=on_text)
            except LLMError as e:
                answer = f"[LLM error] {e}"
            except Exception as e:  # noqa
                answer = f"[error] {e}"
            if not self._closing:
                self.call_from_thread(self._finish, answer)

        self._worker_thread = threading.Thread(target=worker, name="bittu-agent", daemon=True)
        self._worker_thread.start()

    def _stream_delta(self, delta: str) -> None:
        """Buffer streaming deltas and update ONE widget in place.

        Purana bug: har flush par poora badhta hua text RichLog me dubara
        likha jata tha -> duplicate copies + forced auto-scroll, jisse
        scrolling toot jaati thi. Ab ek hi Static widget update hota hai.
        """
        now = time.monotonic()
        if not self._stream_started:
            self._stream_text = Text(f"{BRAND}: ", style="#e8a13a bold")
            self._stream_text.append(delta, style="#d9d9d9")
            self._stream_delta_buf = ""
            self._stream_last_flush = now
            self._stream_widget = self._add_msg(self._stream_text)
            self._stream_started = True
        else:
            self._stream_delta_buf += delta
            # Flush batched tokens every 100ms for smooth, efficient rendering.
            if now - self._stream_last_flush >= 0.1 or len(self._stream_delta_buf) > 200:
                self._stream_text.append(self._stream_delta_buf, style="#d9d9d9")
                self._stream_delta_buf = ""
                self._stream_last_flush = now
                follow = self._at_bottom()
                # Same widget ko update karo — koi duplicate nahi.
                self._stream_widget.update(self._stream_text)
                if follow:
                    self.call_after_refresh(self._scroll_end)
        # Real-time token count update in status bar.
        self.refresh_status()

    def _finish(self, answer: str) -> None:
        if self._closing:
            return
        self.busy = False
        if getattr(self, "_stream_started", False):
            # Flush any remaining buffered tokens into the same widget.
            if self._stream_delta_buf:
                self._stream_text.append(self._stream_delta_buf, style="#d9d9d9")
                self._stream_delta_buf = ""
            self._stream_widget.update(self._stream_text)
            # If answer has a verification/evidence section (dream mode),
            # append it as a separate message block.
            marker = "─" * 40
            if marker in answer:
                idx = answer.index(marker)
                extra = answer[idx:]
                self._add_msg(Text(extra, style="#9e9e9e"))
            follow = self._at_bottom()
            if follow:
                self.call_after_refresh(self._scroll_end)
            self._stream_started = False
        else:
            self.log_bittu(answer)
        # F1 — persist conversation after each turn.
        self.session.messages = self.agent.history
        try:
            self.session.save()
        except OSError as exc:
            self.log_system(f"Session save failed: {exc}")
        # F7 — refresh token count + stop spinner.
        self._worker_thread = None
        self._work_start = 0.0
        self.refresh_status()

    def resume_session(self, which: str) -> str:  # F1
        sess = Session.latest() if which in ("", "last") else Session.load(which)
        if sess is None:
            return f"Session not found: {which}"
        self.session = sess
        self.agent = Agent(self.cfg)
        self._wire_agent_callbacks()
        self.agent.history = list(sess.messages)
        self.agent._approx_tokens = len(str(self.agent.history)) // 4
        self.agent._auto_context_done = True
        # Replay transcript.
        try:
            self._transcript().remove_children()
        except Exception:
            pass
        for m in sess.messages:
            role, content = m.get("role"), (m.get("content") or "")
            if role == "user" and content and not content.startswith("["):
                self.log_user(content)
            elif role == "assistant" and content:
                self.log_bittu(content)
        return f"Resumed session {sess.id} ({len(sess.messages)} messages)"

    def run_agent_task(self, task: str) -> str:
        """Used by slash commands that want the agent to do work."""
        self.log_user(f"(auto) {task[:60]}…")
        self._run_agent_async(task)
        return ""

    # --- actions used by slash commands / bindings ------------------------
    def action_cycle_mode(self) -> str:
        return self.cycle_mode()

    def cycle_mode(self) -> str:
        self.mode_index = (self.mode_index + 1) % len(MODES)
        self.refresh_status()
        return f"Mode: {self._mode_name()}"

    def set_mode(self, name: str) -> str:
        for i, m in enumerate(MODES):
            if m.lower() == name.lower():
                self.mode_index = i
                self.refresh_status()
                return f"Mode: {m}"
        return f"Unknown mode: {name} (plan|build|chat)"

    def action_clear_convo(self) -> None:
        self.reset_conversation()

    def reset_conversation(self) -> None:
        self.agent = Agent(self.cfg)
        self._wire_agent_callbacks()
        self.session = Session.new(self.cfg.model, self.cfg.workdir)
        self._stream_started = False
        self._stream_text = None
        self._stream_widget = None
        try:
            self._transcript().remove_children()
        except Exception:
            pass

    def change_workdir(self, path: str) -> str:
        p = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(p):
            return f"Not a directory: {path}"
        self.cfg.workdir = p
        self.agent = Agent(self.cfg)
        self._wire_agent_callbacks()
        self.session = Session.new(self.cfg.model, self.cfg.workdir)
        self.refresh_status()
        return f"Working directory: {p}"

    def open_login(self) -> str:
        return ("Login: set your key via env ZEDPY_API_KEY, or edit config.py.\n"
                f"Current model: {self.cfg.model}  ·  endpoint: {self.cfg.base_url}")


def run() -> None:
    cfg = Config.load()
    app = BittuApp(cfg)
    # mouse=False -> Textual mouse capture band, terminal ka native
    # text-select / copy kaam karega (Ctrl+C ya mouse drag se select karke copy).
    # PasteInput ensures clipboard paste (Ctrl+V / Shift+Insert) kaam kare
    # aur paste auto-send NA ho.  Long text paste bhi supported hai.
    app.run(mouse=False)
