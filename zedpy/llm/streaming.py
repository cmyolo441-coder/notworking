"""Bounded OpenAI-compatible SSE streaming client."""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from ..config import Config

_MAX_STREAM_BYTES = 8 * 1024 * 1024
_MAX_LINE_BYTES = 1 * 1024 * 1024


def stream_chat(cfg: Config, messages: list[dict], tools: list[dict] | None,
                on_text, cancel_event=None):
    """Stream a completion and return the assembled assistant message."""
    if not cfg.api_key:
        raise RuntimeError("API key set nahi hai")
    parsed = urlparse((cfg.base_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("Invalid LLM base URL: expected http(s) URL")
    if not isinstance(messages, list) or not messages:
        raise RuntimeError("LLM messages list empty hai")
    try:
        max_tokens = max(256, min(int(getattr(cfg, "max_tokens", 1_024)), 2_000_000))
    except (TypeError, ValueError):
        max_tokens = 1_024
    try:
        temperature = max(0.0, min(float(getattr(cfg, "temperature", 0.2)), 2.0))
    except (TypeError, ValueError):
        temperature = 0.2
    try:
        timeout = max(5, min(int(getattr(cfg, "timeout", 300)), 600))
    except (TypeError, ValueError):
        timeout = 300

    payload: dict = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.api_key}",
        "User-Agent": "zedpy/2.1",
        "Accept": "text/event-stream",
    }

    def make_request() -> urllib.request.Request:
        return urllib.request.Request(
            cfg.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    response = None
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = urllib.request.urlopen(make_request(), timeout=timeout)
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read(2_000).decode("utf-8", errors="replace")
            if exc.code == 400 and "max" in detail.lower() and "token" in detail.lower():
                old = int(payload.get("max_tokens", 1_024))
                new = max(256, int(old * 0.6))
                if new < old:
                    payload["max_tokens"] = new
                    continue
            last_error = RuntimeError(f"HTTP {exc.code}: {detail[:500]}")
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise last_error from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            last_error = RuntimeError(f"Streaming network error: {exc}")
            if attempt == 2:
                raise last_error from exc
        if attempt < 2:
            time.sleep(min(2 ** attempt, 4) + 0.2)
    if response is None:
        raise last_error or RuntimeError("Streaming connection failed")

    full_text = ""
    tool_parts: dict[int, dict] = {}
    usage: dict | None = None
    total_bytes = 0
    cancelled = False
    try:
        with response as resp:
            for raw in resp:
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    break
                total_bytes += len(raw)
                if total_bytes > _MAX_STREAM_BYTES:
                    raise RuntimeError("Streaming response size limit se zyada hai")
                if len(raw) > _MAX_LINE_BYTES:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                choices = chunk.get("choices") or []
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    continue
                delta = choices[0].get("delta") or {}
                if not isinstance(delta, dict):
                    continue
                text = delta.get("content") or delta.get("reasoning") or ""
                if isinstance(text, str) and text:
                    full_text += text
                    on_text(text)
                for tool_call in delta.get("tool_calls") or []:
                    if not isinstance(tool_call, dict):
                        continue
                    try:
                        index = int(tool_call.get("index", 0))
                    except (TypeError, ValueError):
                        index = 0
                    part = tool_parts.setdefault(index, {"id": "", "name": "", "arguments": ""})
                    if isinstance(tool_call.get("id"), str):
                        part["id"] = tool_call["id"]
                    function = tool_call.get("function") or {}
                    if not isinstance(function, dict):
                        continue
                    if isinstance(function.get("name"), str):
                        part["name"] = function["name"]
                    if isinstance(function.get("arguments"), str):
                        part["arguments"] += function["arguments"]
    except socket.timeout as exc:
        raise RuntimeError(f"Streaming timeout after {timeout}s") from exc

    tool_calls = [
        {"id": part["id"], "type": "function",
         "function": {"name": part["name"], "arguments": part["arguments"]}}
        for part in tool_parts.values() if part["name"]
    ]
    if usage is None:
        usage = {
            "prompt_tokens": sum(len(str(m.get("content") or "")) for m in messages) // 4,
            "completion_tokens": max(1, len(full_text) // 4),
        }
    return {
        "role": "assistant",
        "content": full_text or ("(stopped)" if cancelled else ""),
        "tool_calls": [] if cancelled else tool_calls,
        "_usage": usage,
    }
