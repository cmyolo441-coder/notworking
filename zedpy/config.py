"""Configuration for the zedpy agent — enterprise-grade settings.

Defaults are here (opencode zen endpoint + mimo-v2.5-free). Override via env:

    ZEDPY_API_KEY     -> API key
    ZEDPY_BASE_URL    -> chat completions endpoint (full URL)
    ZEDPY_MODEL       -> model id
    ZEDPY_MAX_STEPS   -> ReAct loop max steps (default 80)
    ZEDPY_MAX_TOKENS  -> max output tokens (default 1M)
    ZEDPY_EFFORT      -> effort level (normal|max|ultra|ultracombomax|goal|dream)
    ZEDPY_WORKDIR     -> working directory override
    ZEDPY_AUTO_APPROVE -> auto-approve all actions (true/false)

SECURITY NOTE: The default key below is in plaintext for convenience.
In production, use ZEDPY_API_KEY env var and rotate regularly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

# --- Built-in defaults ---
# API key: prefer environment variable; fallback is a placeholder (not a real key).
DEFAULT_API_KEY = os.environ.get("ZEDPY_API_KEY", "")
OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY", DEFAULT_API_KEY)
DEFAULT_BASE_URL = os.environ.get(
    "ZEDPY_BASE_URL",
    "https://opencode.ai/zen/v1/chat/completions",
)
DEFAULT_MODEL = "mimo-v2.5-free"
DEFAULT_MAX_STEPS = 80
DEFAULT_MAX_TOKENS = 1000000
DEFAULT_TIMEOUT = 300

# Cloudflare Workers AI defaults
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")
CF_API_KEY = os.environ.get("CF_API_KEY", "")
CF_BASE_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    "/ai/v1/chat/completions"
    if CF_ACCOUNT_ID else ""
)

# NVIDIA NIM defaults
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


@dataclass
class ModelProfile:
    """Pre-configured model profiles for common use-cases."""
    name: str
    model: str
    base_url: str
    max_tokens: int = 1_000_000
    temperature: float = 0.2
    supports_streaming: bool = True
    supports_tools: bool = True


# Built-in model profiles — user /model can select these.
MODEL_PROFILES: dict[str, ModelProfile] = {
    # === OpenCode Provider ===
    "mimo": ModelProfile(
        name="mimo", model="mimo-v2.5-free",
        base_url="https://opencode.ai/zen/v1/chat/completions",
    ),
    "fast": ModelProfile(
        name="fast", model="mimo-v2.5-free",
        base_url="https://opencode.ai/zen/v1/chat/completions",
        max_tokens=500_000,
    ),
    "deepseek-v4-flash-free": ModelProfile(
        name="deepseek-v4-flash-free", model="deepseek-v4-flash-free",
        base_url="https://opencode.ai/zen/v1/chat/completions",
    ),
    "big-pickle": ModelProfile(
        name="big-pickle", model="big-pickle",
        base_url="https://opencode.ai/zen/v1/chat/completions",
    ),
    # === Cloudflare Workers AI models ===
    # NOTE: CF models have shared context windows (input+output combined).
    # max_tokens = total - headroom for input tokens.
    "glm": ModelProfile(
        name="glm", model="@cf/zai-org/glm-5.2",
        base_url=CF_BASE_URL,
        max_tokens=250_000,   # 256K total - 6K input headroom
        supports_tools=False,  # Cloudflare AI doesn't support tool calling yet
    ),
    "kimi": ModelProfile(
        name="kimi", model="@cf/moonshotai/kimi-k2.7-code",
        base_url=CF_BASE_URL,
        max_tokens=200_000,   # 262K total - 62K input headroom
        supports_tools=False,
    ),
    # === NVIDIA NIM models ===
    # Source: docs.api.nvidia.com + z.ai docs (verified July 2026)
    "glm-5.1": ModelProfile(
        name="glm-5.1", model="z-ai/glm-5.1",
        base_url=NVIDIA_BASE_URL,
        max_tokens=131072,  # GLM-5.1: 120K output tokens
    ),
    "glm-5.2": ModelProfile(
        name="glm-5.2", model="z-ai/glm-5.2",
        base_url=NVIDIA_BASE_URL,
        max_tokens=131072,  # GLM-5.2: 1M context, 131K output tokens
    ),
    "minimax-m3": ModelProfile(
        name="minimax-m3", model="minimaxai/minimax-m3",
        base_url=NVIDIA_BASE_URL,
        max_tokens=65536,  # NVIDIA NIM: 64K output (verified from HuggingFace benchmark)
    ),
    "step-3.7-flash": ModelProfile(
        name="step-3.7-flash", model="stepfun-ai/step-3.7-flash",
        base_url=NVIDIA_BASE_URL,
        max_tokens=16384,  # Step-3.7-Flash official limit
    ),
    # === Dream Mode Optimized (fast response) ===
    "dream-fast": ModelProfile(
        name="dream-fast", model="mimo-v2.5-free",
        base_url="https://opencode.ai/zen/v1/chat/completions",
        max_tokens=500_000,
        temperature=0.1,  # Lower = more focused
    ),
    "dream-pro": ModelProfile(
        name="dream-pro", model="deepseek-v4-flash-free",
        base_url="https://opencode.ai/zen/v1/chat/completions",
        max_tokens=500_000,
        temperature=0.05,
    ),
}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _valid_base_url(value: str) -> str:
    candidate = (value or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return DEFAULT_BASE_URL
    return candidate.rstrip("/")


@dataclass
class Config:
    api_key: str = DEFAULT_API_KEY
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    max_steps: int = DEFAULT_MAX_STEPS
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 0.2
    timeout: int = DEFAULT_TIMEOUT
    workdir: str = ""
    auto_approve: bool = False
    plan_mode: bool = False
    auto_test: bool = False
    test_command: str = ""
    effort: str = "normal"
    # Advanced configuration
    context_window_limit: int = 200_000  # Max tokens before compression triggers
    summary_ratio: float = 0.3  # When compressing, keep this fraction of history
    max_concurrent_tools: int = 5  # Parallel tool execution limit
    enable_caching: bool = True  # Cache repeated LLM calls for identical prompts
    debug_mode: bool = False  # Extra logging
    yolo_mode: bool = False  # Alias for auto_approve

    @classmethod
    def load(cls) -> "Config":
        """Load environment overrides with validation and safe bounds."""
        auto_approve = os.getenv("ZEDPY_AUTO_APPROVE", "").lower() in ("true", "1", "yes")
        effort = os.getenv("ZEDPY_EFFORT", "normal").strip().lower() or "normal"
        requested_workdir = Path(os.getenv("ZEDPY_WORKDIR", "") or os.getcwd()).expanduser()
        try:
            workdir_path = requested_workdir.resolve(strict=True)
            if not workdir_path.is_dir():
                raise ValueError("not a directory")
        except (OSError, ValueError):
            workdir_path = Path.cwd().resolve()

        # Resolve API key: environment first, then a local key file. Never log it.
        api_key = os.getenv("ZEDPY_API_KEY", "").strip() or os.getenv("OPENCODE_API_KEY", "").strip() or DEFAULT_API_KEY
        if not api_key:
            config_paths = [
                workdir_path / ".zedpy" / "api_key",
                Path.home() / ".config" / "zedpy" / "api_key",
                Path.home() / ".zedpy_api_key",
            ]
            for key_path in config_paths:
                try:
                    if key_path.is_file() and (key_path.stat().st_mode & 0o077) == 0:
                        candidate = key_path.read_text(encoding="utf-8").strip()
                        if candidate:
                            api_key = candidate
                            break
                except OSError:
                    continue

        base_url = _valid_base_url(os.getenv("ZEDPY_BASE_URL", DEFAULT_BASE_URL))
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=os.getenv("ZEDPY_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            max_steps=_env_int("ZEDPY_MAX_STEPS", DEFAULT_MAX_STEPS, 1, 500),
            max_tokens=_env_int("ZEDPY_MAX_TOKENS", DEFAULT_MAX_TOKENS, 256, 2_000_000),
            temperature=_env_float("ZEDPY_TEMPERATURE", 0.2, 0.0, 2.0),
            timeout=_env_int("ZEDPY_TIMEOUT", DEFAULT_TIMEOUT, 5, 3_600),
            workdir=str(workdir_path),
            auto_approve=auto_approve,
            effort=effort,
            context_window_limit=_env_int("ZEDPY_CONTEXT_LIMIT", 200_000, 1_024, 2_000_000),
            max_concurrent_tools=_env_int("ZEDPY_MAX_CONCURRENT_TOOLS", 5, 1, 32),
            debug_mode=os.getenv("ZEDPY_DEBUG", "").lower() in ("true", "1", "yes"),
            yolo_mode=auto_approve,
        )

    def apply_profile(self, name: str) -> bool:
        """Apply a named model profile. Returns True if found.

        Cloudflare profiles auto-set the CF API key.
        NVIDIA profiles auto-set the NVIDIA API key.
        OpenCode profiles use the OPENCODE_API_KEY.
        """
        profile = MODEL_PROFILES.get((name or "").lower())
        if profile is None or not profile.base_url:
            return False
        self.model = profile.model
        self.base_url = profile.base_url
        self.max_tokens = profile.max_tokens
        self.temperature = max(0.0, min(float(profile.temperature), 2.0))
        # Auto-switch API key based on provider.
        if "cloudflare.com" in profile.base_url:
            self.api_key = CF_API_KEY
        elif "nvidia.com" in profile.base_url:
            self.api_key = NVIDIA_API_KEY
        elif "opencode.ai" in profile.base_url:
            self.api_key = OPENCODE_API_KEY
        else:
            # Restore default API key for other providers
            self.api_key = os.environ.get("ZEDPY_API_KEY", DEFAULT_API_KEY)
        return True
