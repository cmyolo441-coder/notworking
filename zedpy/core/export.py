"""Feature #18 — Export conversation to Markdown or HTML.

Current session ke messages ko ek readable file me export karta hai.
"""
from __future__ import annotations

import html
import time
from pathlib import Path


def export(messages: list[dict], workdir: str, fmt: str = "md") -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(workdir)
    if fmt == "html":
        path = out_dir / f"bittu-chat-{ts}.html"
        path.write_text(_to_html(messages), encoding="utf-8")
    else:
        path = out_dir / f"bittu-chat-{ts}.md"
        path.write_text(_to_md(messages), encoding="utf-8")
    return f"Exported conversation to {path.name}"


def _to_md(messages: list[dict]) -> str:
    out = ["# BITTU Conversation\n"]
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role == "system" or not content or content.startswith("["):
            continue
        if role == "user":
            out.append(f"## 🧑 User\n\n{content}\n")
        elif role == "assistant":
            out.append(f"## 🤖 BITTU\n\n{content}\n")
    return "\n".join(out)


def _to_html(messages: list[dict]) -> str:
    rows = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role == "system" or not content or content.startswith("["):
            continue
        color = "#e8a13a" if role == "assistant" else "#4a9eff"
        who = "BITTU" if role == "assistant" else "User"
        rows.append(
            f'<div style="margin:16px 0"><b style="color:{color}">{who}</b>'
            f'<pre style="white-space:pre-wrap;background:#161616;padding:12px;'
            f'border-radius:8px;color:#ddd">{html.escape(content)}</pre></div>'
        )
    return (
        '<html><body style="background:#0a0a0a;color:#ddd;font-family:monospace;'
        'max-width:820px;margin:40px auto;padding:0 20px">'
        '<h1 style="color:#e8a13a">BITTU Conversation</h1>' + "".join(rows) + "</body></html>"
    )
