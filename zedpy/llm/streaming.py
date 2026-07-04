"""Feature 4 — Streaming responses (SSE).

LLM se token-by-token text stream karta hai taaki UI me real-time type hota dikhe.
Tool calls ko bhi assemble karta hai. Pure stdlib (urllib + manual SSE parse).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import Config


def stream_chat(cfg: Config, messages: list[dict], tools: list[dict] | None,
                on_text, cancel_event=None):
    """Stream a completion.

    `on_text(delta)` har text chunk par call hota hai (live rendering ke liye).
    `cancel_event` (threading.Event) — agar set ho jaaye to streaming roko.
    Return: full assistant message dict {content, tool_calls}.
    """
    payload: dict = {
        "model": cfg.model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": cfg.max_tokens,
        "stream": True,
        # F7 — server se streaming ke saath final usage bhi maango (OpenAI-compat).
        "stream_options": {"include_usage": True},
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    req = urllib.request.Request(
        cfg.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
            "User-Agent": "zedpy/1.0 (+https://opencode.ai)",
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    full_text = ""
    tool_parts: dict[int, dict] = {}
    usage: dict | None = None

    cancelled = False
    for _retry in range(3):
        try:
            resp_handle = urllib.request.urlopen(req, timeout=4000)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            if e.code == 400 and "max" in detail.lower() and "token" in detail.lower():
                old = payload.get("max_tokens", 0)
                new = max(1024, int(old * 0.6))
                payload["max_tokens"] = new
                req = urllib.request.Request(
                    cfg.base_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=req.headers,
                    method="POST",
                )
                continue
            raise
    else:
        raise RuntimeError("Failed to connect after retries")

    with resp_handle as resp:
        for raw in resp:
            # Cancel check — user ne Esc dabaya to streaming band.
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            # F7 — final usage chunk (choices khaali, usage bhara hota hai).
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            # Text (kuch models 'reasoning' bhejte hain).
            txt = delta.get("content") or delta.get("reasoning") or ""
            if txt:
                full_text += txt
                on_text(txt)
            # Tool calls assemble.
            for tc in delta.get("tool_calls", []) or []:
                idx = tc.get("index", 0)
                part = tool_parts.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                if tc.get("id"):
                    part["id"] = tc["id"]
                fn = tc.get("function", {})
                if fn.get("name"):
                    part["name"] = fn["name"]
                if fn.get("arguments"):
                    part["arguments"] += fn["arguments"]

    tool_calls = [
        {"id": p["id"], "type": "function",
         "function": {"name": p["name"], "arguments": p["arguments"]}}
        for p in tool_parts.values() if p["name"]
    ]
    # F7 — usage server se aaya to wahi; warna streamed text se estimate
    # (~4 chars/token) taaki token counter real-time me badhta dikhe.
    if usage is None:
        approx_out = max(1, len(full_text) // 4)
        approx_in = sum(len(str(m.get("content") or "")) for m in messages) // 4
        usage = {"prompt_tokens": approx_in, "completion_tokens": approx_out}
    if cancelled:
        return {"role": "assistant", "content": full_text or "(stopped)",
                "tool_calls": [], "_usage": usage}
    return {"role": "assistant", "content": full_text,
            "tool_calls": tool_calls, "_usage": usage}
