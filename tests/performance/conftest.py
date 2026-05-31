"""Performance test fixtures and thresholds for latebra.

Defines the baseline metrics and shared fixtures used by all performance
tests. Adjust thresholds in ``PERF_THRESHOLDS`` as the project improves.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# -- Thresholds ---------------------------------------------------------------
# All values are MAXIMUM allowed (test FAILS if exceeded).
# Document the date and commit hash of each baseline recalibration.

PERF_THRESHOLDS: dict[str, float] = {
    # Layer 1: pure HTTP request (curl_cffi, no TLS impersonation overhead)
    "request_layer_first_byte_ms": 3000,      # 3s  — first response byte
    "request_layer_total_ms": 5000,            # 5s  — complete fetch
    # Layer 2: browser engines
    "browser_cold_launch_ms": 12000,           # 12s — first launch + navigation
    "browser_warm_navigation_ms": 5000,        # 5s  — navigation on warm browser
    "browser_patchright_total_ms": 15000,      # 15s — full scrape with patchright
    "browser_camoufox_total_ms": 20000,        # 20s — full scrape with camoufox
    "browser_nodriver_total_ms": 18000,        # 18s — full scrape with nodriver
    # Pipeline fallback
    "pipeline_request_success_ms": 8000,       # 8s  — happy path (curl_cffi wins)
    "pipeline_browser_fallback_ms": 30000,     # 30s — worst case fallback
    # MCP server
    "mcp_tool_roundtrip_ms": 10000,            # 10s — tool call + response
    # Memory
    "memory_growth_100_ops_mb": 100,           # 100MB max growth after 100 ops
    "memory_per_op_avg_mb": 2.0,               # 2MB average per operation
    # Anonymity
    "anonymity_pass_rate": 0.80,               # 80% minimum pass rate
    # Cache
    "cache_hit_latency_ms": 100,               # 100ms — cache lookup
    "cache_miss_latency_ms": 500,              # 500ms — cache miss + insert
}


# -- Baseline recording --------------------------------------------------------

BASELINE_DIR = Path(__file__).parent / ".baselines"


def record_baseline() -> None:
    """Record current threshold values as a timestamped baseline snapshot."""
    BASELINE_DIR.mkdir(exist_ok=True)
    import json
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filepath = BASELINE_DIR / f"baseline_{ts}.json"
    filepath.write_text(json.dumps(PERF_THRESHOLDS, indent=2) + "\n")


def load_latest_baseline() -> dict[str, float] | None:
    """Load the most recent baseline snapshot, if any."""
    if not BASELINE_DIR.exists():
        return None
    files = sorted(BASELINE_DIR.glob("baseline_*.json"))
    if not files:
        return None
    import json
    return json.loads(files[-1].read_text())


# -- Shared fixtures -----------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async performance tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def perf_timer():
    """Return a high-resolution timer for consistent measurements."""
    return time.perf_counter


@pytest.fixture
def measured_url() -> str:
    """Default test URL — overridable via env for CI vs local."""
    return os.environ.get(
        "LATEBRA_PERF_TEST_URL",
        "https://httpbin.org/html",
    )


@pytest.fixture
def heavy_url() -> str:
    """URL for throughput/stress testing (larger payload)."""
    return os.environ.get(
        "LATEBRA_PERF_HEAVY_URL",
        "https://httpbin.org/bytes/10240",
    )


@pytest.fixture
def anonymity_url() -> str:
    """URL for anonymity testing — browser fingerprint detection."""
    return os.environ.get(
        "LATEBRA_PERF_ANON_URL",
        "https://httpbin.org/headers",
    )


def assert_threshold(
    metric_name: str,
    actual_ms: float,
    *,
    tolerance_pct: float = 0.0,
) -> None:
    """Assert that a measured value is within the defined threshold.

    Args:
        metric_name: key in PERF_THRESHOLDS
        actual_ms: measured value in milliseconds
        tolerance_pct: extra tolerance percentage (e.g. 0.10 = 10% grace)
    """
    threshold = PERF_THRESHOLDS.get(metric_name)
    if threshold is None:
        pytest.fail(
            f"Unknown performance metric: {metric_name!r}. "
            f"Available: {sorted(PERF_THRESHOLDS)}"
        )

    allowed = threshold * (1.0 + tolerance_pct)
    if actual_ms > allowed:
        pytest.fail(
            f"\n  PERFORMANCE REGRESSION: {metric_name}\n"
            f"    threshold: {threshold:,.0f}ms\n"
            f"    actual:    {actual_ms:,.0f}ms\n"
            f"    excess:    {actual_ms - threshold:,.0f}ms "
            f"({(actual_ms/threshold - 1)*100:+.1f}%)\n"
            f"  TIP: Run `pytest tests/performance/ --benchmark-compare` to find regressions",
        )


def record_metric(
    metric_name: str,
    value_ms: float,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a performance metric for later comparison.

    Writes to ``tests/performance/results.jsonl`` for trend analysis.
    """
    import json
    from datetime import datetime, timezone
    results_file = Path(__file__).parent / "results.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metric": metric_name,
        "value_ms": round(value_ms, 3),
        "metadata": metadata or {},
    }
    with open(results_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
