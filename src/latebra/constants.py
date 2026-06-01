"""Centralized constants for latebra anti-bot evasion.

All magic numbers, user agents, viewports, and other configuration
values that were previously duplicated across modules live here.

Autor: Evandro Fonseca Junior
Licença: MIT
"""

from __future__ import annotations

import platform
from pathlib import Path

# ── App identity ────────────────────────────────
APP_NAME = "latebra"

# ── Cross-platform directories ──────────────────
_DATA_DIR: Path | None = None
_LOG_DIR: Path | None = None


def _get_data_dir() -> Path:
    """Return cross-platform application data directory (without mkdir)."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local"
    elif system == "Linux":
        base = Path.home() / ".local" / "share"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".latebra"
    return base / APP_NAME


def get_data_dir() -> Path:
    """Get (or create) the application data directory.

    Platform-aware:
    - Linux:   ~/.local/share/latebra/
    - Windows: %LOCALAPPDATA%/latebra/
    - macOS:   ~/Library/Application Support/latebra/
    """
    global _DATA_DIR
    if _DATA_DIR is None:
        _DATA_DIR = _get_data_dir()
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def get_log_dir() -> Path:
    """Get (or create) the logs subdirectory under the data directory.

    Returns:
        Path like ~/.local/share/latebra/logs/ (Linux)
    """
    global _LOG_DIR
    if _LOG_DIR is None:
        _LOG_DIR = get_data_dir() / "logs"
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


# ── Content thresholds ───────────────────────────
MIN_CONTENT_LENGTH: int = 500
"""Minimum content length (bytes) to consider a response successful."""

PREVIEW_MAX_LENGTH: int = 500
"""Max length of content preview returned to MCP clients."""

# ── CAPTCHA polling ──────────────────────────────
CAPTCHA_POLL_MAX_ATTEMPTS: int = 60
"""Max polling attempts for CAPTCHA solving services."""

CAPTCHA_POLL_INTERVAL_2CAPTCHA: int = 5
"""Poll interval in seconds for 2captcha (60 × 5s = 5 min timeout)."""

CAPTCHA_POLL_INTERVAL_CAPSOLVER: int = 3
"""Poll interval in seconds for capsolver (60 × 3s = 3 min timeout)."""

# ── Request defaults ─────────────────────────────
DEFAULT_REQUEST_TIMEOUT: float = 30.0
"""Default HTTP request timeout in seconds."""

DEFAULT_MAX_RETRIES: int = 2
"""Default number of retry attempts for failed requests."""

# ── Cache ────────────────────────────────────────
DEFAULT_CACHE_TTL: int = 3600
"""Default cache TTL in seconds (1 hour)."""

DEFAULT_CACHE_DIR: str = "~/.cache/latebra"
"""Default directory for SQLite cache and other persistent data."""

# ── Proxy circuit breaker ────────────────────────
PROXY_MAX_FAILURES: int = 3
"""Consecutive failures before proxy is banned."""

PROXY_COOLDOWN_BASE: int = 30
"""Base cooldown in seconds. Formula: min(30 * 2^(failures-3), 3600)."""

PROXY_COOLDOWN_MAX: int = 3600
"""Maximum proxy cooldown in seconds (1 hour)."""

# ── User agents ──────────────────────────────────
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# ── Viewport dimensions ──────────────────────────
VIEWPORTS: list[tuple[int, int]] = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
    (1680, 1050),
]

# ── Platforms ────────────────────────────────────
PLATFORMS: list[str] = ["Win32", "MacIntel", "Linux x86_64"]

# ── Timezones ────────────────────────────────────
TIMEZONES: list[str] = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
    "Asia/Tokyo",
    "America/Sao_Paulo",
]

# ── Languages ────────────────────────────────────
LANGUAGES: list[list[str]] = [
    ["en-US", "en"],
    ["en-GB", "en"],
    ["en-CA", "en"],
    ["en-US", "en", "pt-BR"],
    ["en", "fr"],
]

# ── Locales ──────────────────────────────────────
LOCALES: list[str] = ["en-US", "en-GB", "en-CA", "en-AU"]

# ── TLS impersonation ────────────────────────────
IMPERSONATE_OPTIONS: list[str] = [
    "chrome120",
    "chrome123",
    "chrome124",
    "safari15_5",
    "safari17_0",
    "edge120",
    "firefox120",
]

# ── Browser engines ──────────────────────────────
ENGINES: list[str] = ["patchright", "camoufox", "nodriver"]

# ── Detection markers ────────────────────────────
DETECTION_MARKERS: list[str] = [
    "automated",
    "bot",
    "captcha",
    "cloudflare",
    "blocked",
    "denied",
    "unusual traffic",
]

# ── Canvas / Audio noise bounds ──────────────────
CANVAS_NOISE_MIN: float = 0.0005
CANVAS_NOISE_MAX: float = 0.002
AUDIO_NOISE_MIN: float = 0.00001
AUDIO_NOISE_MAX: float = 0.0001

# ── Device scale factors ─────────────────────────
DEVICE_SCALE_FACTORS: list[float] = [1.0, 1.25, 1.5, 2.0]

# ── Hardware concurrency options ─────────────────
HARDWARE_CONCURRENCY_OPTIONS: list[int] = [4, 6, 8, 12, 16]

# ── Device memory options (GB) ───────────────────
DEVICE_MEMORY_OPTIONS: list[int] = [4, 8, 16]
