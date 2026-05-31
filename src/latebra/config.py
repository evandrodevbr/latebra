"""Centralized configuration for latebra.

Loads from environment variables with sensible defaults.
Eliminates constructor-chain parameter threading across 4 levels
(serve → LatebraServer → SmartScrapePipeline → CaptchaSolver).

Autor: Evandro Fonseca Junior
Licença: MIT
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from latebra.constants import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_TTL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT,
)


@dataclass
class LatebraConfig:
    """Centralized configuration loaded from environment variables.

    Usage:
        config = LatebraConfig.from_env()
        pipeline = SmartScrapePipeline(config)
        server = LatebraServer(pipeline)
    """

    # ── Proxy ─────────────────────────────────────
    proxies: list[str] = field(default_factory=list)
    """Proxy URLs (e.g., 'socks5://user:pass@host:1080')."""

    # ── CAPTCHA ───────────────────────────────────
    two_captcha_key: str | None = None
    """API key for 2captcha.com."""

    capsolver_key: str | None = None
    """API key for capsolver.com."""

    # ── Cache ─────────────────────────────────────
    cache_dir: str = DEFAULT_CACHE_DIR
    cache_ttl: int = DEFAULT_CACHE_TTL
    use_cache: bool = True

    # ── Stealth ───────────────────────────────────
    stealth_enabled: bool = True

    # ── Request ───────────────────────────────────
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES

    # ── Logging ───────────────────────────────────
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, prefix: str = "LATEBRA_") -> LatebraConfig:
        """Create config from environment variables.

        Environment variables:
            LATEBRA_PROXIES: comma-separated proxy URLs
            LATEBRA_2CAPTCHA_KEY: 2captcha API key
            LATEBRA_CAPSOLVER_KEY: capsolver API key
            LATEBRA_CACHE_DIR: cache directory path
            LATEBRA_CACHE_TTL: cache TTL in seconds
            LATEBRA_STEALTH_ENABLED: 'true'/'1' to enable
            LATEBRA_REQUEST_TIMEOUT: HTTP timeout in seconds
            LATEBRA_MAX_RETRIES: retry count
            LATEBRA_LOG_LEVEL: logging level
        """
        return cls(
            proxies=_parse_proxies(os.getenv(f"{prefix}PROXIES", "")),
            two_captcha_key=os.getenv(f"{prefix}2CAPTCHA_KEY"),
            capsolver_key=os.getenv(f"{prefix}CAPSOLVER_KEY"),
            cache_dir=os.path.expanduser(
                os.getenv(f"{prefix}CACHE_DIR", DEFAULT_CACHE_DIR)
            ),
            cache_ttl=int(os.getenv(f"{prefix}CACHE_TTL", str(DEFAULT_CACHE_TTL))),
            use_cache=os.getenv(f"{prefix}CACHE_ENABLED", "true").lower()
            not in ("false", "0", "no"),
            stealth_enabled=os.getenv(f"{prefix}STEALTH_ENABLED", "true").lower()
            not in ("false", "0", "no"),
            request_timeout=float(
                os.getenv(f"{prefix}REQUEST_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT))
            ),
            max_retries=int(
                os.getenv(f"{prefix}MAX_RETRIES", str(DEFAULT_MAX_RETRIES))
            ),
            log_level=os.getenv(f"{prefix}LOG_LEVEL", "INFO").upper(),
        )


def _parse_proxies(raw: str) -> list[str]:
    """Parse comma-separated proxy string into validated list."""
    if not raw or not raw.strip():
        return []
    proxies = [p.strip() for p in raw.split(",") if p.strip()]
    # Basic validation: each proxy must have scheme://
    valid = []
    for p in proxies:
        if "://" in p:
            valid.append(p)
    return valid
