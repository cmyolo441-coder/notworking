"""Enterprise LLM client with caching, retry, and timeout configuration.

Features:
  - LRU response cache to avoid redundant API calls (big speedup for dream mode)
  - Exponential backoff with jitter for retries
  - Per-request timeout configuration
  - Token usage tracking with cost estimation
  - Structured logging of all LLM calls
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
import random
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from typing import Any

from ..config import Config

logger = logging.getLogger("zedpy.llm")

# Retryable HTTP status codes (transient failures).
_RETRYABLE = {429, 500, 502, 503, 504}

# Default timeout for LLM requests (seconds).
_DEFAULT_TIMEOUT = 4000


class LLMError(Exception):
    """Raised when an LLM request fails after all retry attempts."""
    pass


class ResponseCache:
    """LRU cache for LLM responses keyed by (model, messages_hash).

    Dream mode often sends the same system prompt + project context repeatedly.
    Caching avoids redundant API calls for identical requests, giving a massive
    speed boost.

    Max size: 64 entries (configurable). TTL: 10 minutes (configurable).
    """

    def __init__(self, max_size: int = 64, ttl_seconds: float = 600):
        self._cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _key(self, model: str, messages: list[dict], tools: list[dict] | None) -> str:
        """Generate a cache key from request parameters."""
        # Only cache based on model + serialized messages (tools rarely change).
        payload = json.dumps({"model": model, "messages": messages},
                             sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()[:24]

    def get(self, model: str, messages: list[dict], tools: list[dict] | None) -> dict | None:
        """Look up a cached response. Returns None on miss or expiry."""
        key = self._key(model, messages, tools)
        if key in self._cache:
            ts, response = self._cache[key]
            if time.monotonic() - ts < self._ttl:
                self._cache.move_to_end(key)
                self._hits += 1
                logger.debug("LLM cache HIT (hits=%d, misses=%d)", self._hits, self._misses)
                return response
            # Expired — remove.
            del self._cache[key]
        self._misses += 1
        return None

    def put(self, model: str, messages: list[dict], tools: list[dict] | None,
            response: dict) -> None:
        """Store a response in the cache."""
        key = self._key(model, messages, tools)
        self._cache[key] = (time.monotonic(), response)
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total else "0%",
            "size": len(self._cache),
        }

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# Global cache instance (module-level, shared across agents).
_cache = ResponseCache()


class LLM:
    """Enterprise LLM client with caching, retry, and structured logging."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._request_count = 0
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_latency = 0.0

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             max_attempts: int = 8, use_cache: bool = True,
             timeout: int | None = None) -> dict:
        """Send a chat completion request with caching and retry.

        Response includes 'content' (str|None) and optionally 'tool_calls'.
        Caching is ON by default for non-streaming requests.
        """
        if not self.cfg.api_key:
            # Provider-specific error messages
            if "nvidia.com" in self.cfg.base_url:
                raise LLMError(
                    "NVIDIA API key set nahi hai.\n"
                    "Set env: export NVIDIA_API_KEY='nvapi-...'\n"
                    "Or save key to: ~/.config/zedpy/api_key"
                )
            elif "cloudflare.com" in self.cfg.base_url:
                raise LLMError(
                    "Cloudflare API key set nahi hai.\n"
                    "Set env: export CF_API_KEY='cfut_...'"
                )
            else:
                raise LLMError(
                    "API key set nahi hai.\n"
                    "Set env: export ZEDPY_API_KEY='your-key'\n"
                    "Or save key to: ~/.config/zedpy/api_key"
                )

        # Check cache first (huge speed boost for dream mode).
        if use_cache:
            cached = _cache.get(self.cfg.model, messages, tools)
            if cached is not None:
                logger.info("LLM cache HIT — skipping API call")
                return cached

        # Build request payload.
        effective_timeout = timeout or self.cfg.timeout or _DEFAULT_TIMEOUT
        payload: dict = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": self.cfg.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        data = json.dumps(payload).encode("utf-8")
        last_err: Exception | None = None
        t_start = time.monotonic()

        for attempt in range(1, max_attempts + 1):
            req = urllib.request.Request(
                self.cfg.base_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.cfg.api_key}",
                    "User-Agent": "zedpy/2.0 (+https://opencode.ai)",
                    "Accept": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))

                result = self._extract(body)
                elapsed = time.monotonic() - t_start
                self._track_request(body, elapsed)

                # Cache the successful response.
                if use_cache:
                    _cache.put(self.cfg.model, messages, tools, result)

                logger.info("LLM response: %.2fs, tokens=%d/%d, cache=%s",
                            elapsed,
                            body.get("usage", {}).get("prompt_tokens", 0),
                            body.get("usage", {}).get("completion_tokens", 0),
                            "miss")
                return result

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:500]
                # Auto-recover: CF models reject if max_tokens > context window.
                # Reduce max_tokens and retry immediately (no delay).
                if e.code == 400 and "max" in detail.lower() and "token" in detail.lower():
                    old = payload.get("max_tokens", 0)
                    new = max(1024, int(old * 0.6))
                    payload["max_tokens"] = new
                    data = json.dumps(payload).encode("utf-8")
                    logger.warning("max_tokens too large (%d → %d), retrying", old, new)
                    continue
                # 402 Payment Required — usually means quota/billing issue
                if e.code == 402:
                    raise LLMError(
                        f"402 Payment Required: API key ya quota problem.\n"
                        f"Model: {self.cfg.model}\n"
                        f"Detail: {detail[:200]}\n"
                        f"Solution: Check API key / plan at provider dashboard."
                    ) from e
                if e.code in _RETRYABLE and attempt < max_attempts:
                    # Exponential backoff with jitter.
                    delay = min(2 ** attempt, 30) + random.uniform(0, 1)
                    logger.warning("LLM HTTP %d (attempt %d/%d), retrying in %.1fs",
                                   e.code, attempt, max_attempts, delay)
                    last_err = LLMError(f"HTTP {e.code}: {detail}")
                    time.sleep(delay)
                    continue
                raise LLMError(f"HTTP {e.code} from LLM: {detail}") from e

            except urllib.error.URLError as e:
                if attempt < max_attempts:
                    delay = min(2 ** attempt, 30) + random.uniform(0, 1)
                    logger.warning("LLM network error (attempt %d/%d), retrying: %s",
                                   attempt, max_attempts, e.reason)
                    time.sleep(delay)
                    last_err = LLMError(f"Network error: {e.reason}")
                    continue
                raise LLMError(f"Network error: {e.reason}") from e

        raise last_err or LLMError("LLM request failed after all attempts")

    @staticmethod
    def _extract(body: dict) -> dict:
        """Extract assistant message from API response body."""
        choices = body.get("choices") or []
        if not choices:
            raise LLMError(f"LLM ne koi choice nahi bheji: {str(body)[:300]}")
        msg = choices[0].get("message") or {}
        # Some reasoning models send 'reasoning' instead of 'content'.
        if not msg.get("content") and msg.get("reasoning"):
            msg["content"] = msg["reasoning"]
        # Attach token usage from server response.
        if body.get("usage"):
            msg["_usage"] = body["usage"]
        return msg

    def _track_request(self, body: dict, elapsed: float) -> None:
        """Track request metrics for monitoring."""
        self._request_count += 1
        usage = body.get("usage") or {}
        self._total_tokens_in += usage.get("prompt_tokens", 0)
        self._total_tokens_out += usage.get("completion_tokens", 0)
        self._total_latency += elapsed

    def stats(self) -> dict[str, Any]:
        """Return LLM client statistics."""
        return {
            "requests": self._request_count,
            "total_tokens_in": self._total_tokens_in,
            "total_tokens_out": self._total_tokens_out,
            "avg_latency": f"{self._total_latency / max(1, self._request_count):.2f}s",
            "cache": _cache.stats(),
        }


def get_cache_stats() -> dict[str, Any]:
    """Get global cache statistics (for /stats command)."""
    return _cache.stats()


def clear_cache() -> None:
    """Clear the global LLM response cache."""
    _cache.clear()
