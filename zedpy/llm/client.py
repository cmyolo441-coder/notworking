"""Robust OpenAI-compatible chat-completions client."""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import random
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from typing import Any
from urllib.parse import urlparse

from ..config import Config

logger = logging.getLogger("zedpy.llm")
_RETRYABLE = {429, 500, 502, 503, 504}
_DEFAULT_TIMEOUT = 300
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class LLMError(Exception):
    """Raised when an LLM request fails after all retry attempts."""


class ResponseCache:
    """Thread-safe bounded LRU cache with TTL and defensive copies."""

    def __init__(self, max_size: int = 64, ttl_seconds: float = 600):
        self._cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._max_size = max(1, int(max_size))
        self._ttl = max(1.0, float(ttl_seconds))
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()

    def _key(self, model: str, messages: list[dict], tools: list[dict] | None) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools or [],
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]

    def get(self, model: str, messages: list[dict], tools: list[dict] | None) -> dict | None:
        key = self._key(model, messages, tools)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            timestamp, response = entry
            if time.monotonic() - timestamp >= self._ttl:
                self._cache.pop(key, None)
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug("LLM cache HIT (hits=%d, misses=%d)", self._hits, self._misses)
            return copy.deepcopy(response)

    def put(self, model: str, messages: list[dict], tools: list[dict] | None, response: dict) -> None:
        key = self._key(model, messages, tools)
        with self._lock:
            self._cache[key] = (time.monotonic(), copy.deepcopy(response))
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits / total * 100:.1f}%" if total else "0%",
                "size": len(self._cache),
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0


_cache = ResponseCache()


class LLM:
    """OpenAI-compatible client with caching, bounded retry and observability."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._request_count = 0
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_latency = 0.0
        self._stats_lock = threading.Lock()

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             max_attempts: int = 8, use_cache: bool = True,
             timeout: int | None = None) -> dict:
        """Send a chat completion request and return an assistant message."""
        if not self.cfg.api_key:
            if "nvidia.com" in self.cfg.base_url:
                raise LLMError("NVIDIA API key set nahi hai. Set env: export NVIDIA_API_KEY='nvapi-...'")
            if "cloudflare.com" in self.cfg.base_url:
                raise LLMError("Cloudflare API key set nahi hai. Set env: export CF_API_KEY='cfut_...'")
            raise LLMError("API key set nahi hai. Set env: export ZEDPY_API_KEY='your-key'")

        parsed_url = urlparse((self.cfg.base_url or "").strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise LLMError("Invalid LLM base URL: expected http(s) URL")
        if parsed_url.username or parsed_url.password:
            raise LLMError("LLM URL me embedded credentials allowed nahi hain")
        if not isinstance(messages, list) or not messages:
            raise LLMError("LLM messages list empty hai")

        try:
            attempts = max(1, min(int(max_attempts), 8))
        except (TypeError, ValueError):
            attempts = 3
        try:
            effective_timeout = int(timeout or self.cfg.timeout or _DEFAULT_TIMEOUT)
        except (TypeError, ValueError):
            effective_timeout = _DEFAULT_TIMEOUT
        effective_timeout = max(5, min(effective_timeout, 600))

        cache_model = f"{self.cfg.base_url}|{self.cfg.model}|{self.cfg.max_tokens}|{getattr(self.cfg, 'temperature', 0.2)}"
        if use_cache and getattr(self.cfg, "enable_caching", True):
            cached = _cache.get(cache_model, messages, tools)
            if cached is not None:
                logger.info("LLM cache HIT — skipping API call")
                return cached

        try:
            configured_tokens = int(getattr(self.cfg, "max_tokens", 1_024))
        except (TypeError, ValueError):
            configured_tokens = 1_024
        try:
            configured_temperature = float(getattr(self.cfg, "temperature", 0.2))
        except (TypeError, ValueError):
            configured_temperature = 0.2
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": max(0.0, min(configured_temperature, 2.0)),
            "max_tokens": max(256, min(configured_tokens, 2_000_000)),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise LLMError(f"LLM payload serialize nahi hua: {exc}") from exc

        last_err: Exception | None = None
        started = time.monotonic()
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(
                self.cfg.base_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.cfg.api_key}",
                    "User-Agent": "zedpy/2.1",
                    "Accept": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=effective_timeout) as response:
                    raw = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(raw) > _MAX_RESPONSE_BYTES:
                    raise LLMError("LLM response size limit se zyada hai")
                try:
                    body = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise LLMError(f"LLM ne invalid JSON response diya: {exc}") from exc
                result = self._extract(body)
                elapsed = time.monotonic() - started
                self._track_request(body, elapsed)
                if use_cache and getattr(self.cfg, "enable_caching", True):
                    _cache.put(cache_model, messages, tools, result)
                logger.info("LLM response: %.2fs, tokens=%d/%d", elapsed,
                            (body.get("usage") or {}).get("prompt_tokens", 0),
                            (body.get("usage") or {}).get("completion_tokens", 0))
                return result
            except urllib.error.HTTPError as exc:
                detail = exc.read(2_000).decode("utf-8", errors="replace")
                if exc.code == 400 and "max" in detail.lower() and "token" in detail.lower():
                    old = int(payload.get("max_tokens", 1024))
                    new = max(256, int(old * 0.6))
                    if new < old:
                        payload["max_tokens"] = new
                        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        logger.warning("max_tokens too large (%d -> %d), retrying", old, new)
                        continue
                if exc.code == 402:
                    raise LLMError(f"402 Payment Required: API key ya provider quota problem. Detail: {detail[:200]}") from exc
                if exc.code in _RETRYABLE and attempt < attempts:
                    delay = min(2 ** (attempt - 1), 30) + random.uniform(0, 1)
                    last_err = LLMError(f"HTTP {exc.code}: {detail[:500]}")
                    time.sleep(delay)
                    continue
                raise LLMError(f"HTTP {exc.code} from LLM: {detail[:500]}") from exc
            except urllib.error.URLError as exc:
                last_err = LLMError(f"Network error: {exc.reason}")
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 30) + random.uniform(0, 1))
                    continue
                raise last_err from exc
            except TimeoutError as exc:
                last_err = LLMError(f"LLM request timeout after {effective_timeout}s")
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 30) + random.uniform(0, 1))
                    continue
                raise last_err from exc

        raise last_err or LLMError("LLM request failed after all attempts")

    @staticmethod
    def _extract(body: dict) -> dict:
        if not isinstance(body, dict):
            raise LLMError("LLM response object nahi hai")
        choices = body.get("choices") or []
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise LLMError(f"LLM ne koi valid choice nahi bheji: {str(body)[:300]}")
        msg = choices[0].get("message") or {}
        if not isinstance(msg, dict):
            raise LLMError("LLM choice me invalid message object hai")
        msg = dict(msg)
        if not msg.get("content") and msg.get("reasoning"):
            msg["content"] = msg["reasoning"]
        if body.get("usage"):
            msg["_usage"] = body["usage"]
        return msg

    def _track_request(self, body: dict, elapsed: float) -> None:
        usage = body.get("usage") or {}
        with self._stats_lock:
            self._request_count += 1
            self._total_tokens_in += int(usage.get("prompt_tokens", 0) or 0)
            self._total_tokens_out += int(usage.get("completion_tokens", 0) or 0)
            self._total_latency += elapsed

    def stats(self) -> dict[str, Any]:
        with self._stats_lock:
            requests = self._request_count
            return {
                "requests": requests,
                "total_tokens_in": self._total_tokens_in,
                "total_tokens_out": self._total_tokens_out,
                "avg_latency": f"{self._total_latency / max(1, requests):.2f}s",
                "cache": _cache.stats(),
            }


def get_cache_stats() -> dict[str, Any]:
    return _cache.stats()


def clear_cache() -> None:
    _cache.clear()
