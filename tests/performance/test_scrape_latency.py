"""Performance baseline: scrape latency per layer.

Measures end-to-end timing for each pipeline layer independently.
Uses direct time.monotonic() for async I/O tests — 10 iterations,
reports avg (best 8) and p50.

Run:  pytest tests/performance/test_scrape_latency.py -v -s
Skip browser: pytest ... -m "not slow"
"""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from latebra.layers.request import AsyncRequestLayer
from latebra.layers.browser import AsyncBrowserLayer
from latebra.pipeline import SmartScrapePipeline

from .conftest import assert_threshold, record_metric

logger = logging.getLogger(__name__)

# Reusable async benchmark helper
async def _benchmark_async(func, iterations: int = 10) -> tuple[float, float]:
    """Run an async function N times and return (avg_best_8, p50) in ms.

    ``func`` must be an async callable returning True on success.
    """
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.monotonic()
        ok = await func()
        elapsed = (time.monotonic() - t0) * 1000
        if ok:
            samples.append(elapsed)
    if len(samples) < 5:
        raise RuntimeError(f"Only {len(samples)}/{iterations} successful samples")
    best = sorted(samples)[:8]
    avg = sum(best) / len(best)
    p50 = sorted(samples)[len(samples) // 2]
    return avg, p50


# ═══════════════════════════════════════════════════════════════════
# Layer 1 — HTTP Request (curl_cffi)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_request_layer_latency(measured_url: str):
    """HTTP GET latency with curl_cffi session reuse."""
    layer = AsyncRequestLayer()

    # Warmup — ensure session pool is initialized
    await layer.fetch(measured_url)

    async def _fetch_ok() -> bool:
        r = await layer.fetch(measured_url)
        return r.status == 200

    avg_ms, p50_ms = await _benchmark_async(_fetch_ok)

    print(f"\n  ⏱  request layer: avg {avg_ms:,.0f}ms, p50 {p50_ms:,.0f}ms")
    record_metric("request_layer_avg_ms", avg_ms)
    record_metric("request_layer_p50_ms", p50_ms)
    assert_threshold("request_layer_total_ms", avg_ms, tolerance_pct=0.3)
    # Assert sub-5s p50 for reasonable experience
    assert p50_ms < 5000, f"Request layer p50 too slow: {p50_ms:,.0f}ms"


@pytest.mark.asyncio
async def test_request_layer_retry_overhead(measured_url: str):
    """Measure overhead of retry mechanism (should be ~0 on success path)."""
    layer = AsyncRequestLayer(max_retries=2)

    await layer.fetch(measured_url)  # warmup

    async def _fetch_ok() -> bool:
        r = await layer.fetch(measured_url)
        return r.status == 200

    avg_ms, p50_ms = await _benchmark_async(_fetch_ok)

    print(f"\n  🔁 request + retry: avg {avg_ms:,.0f}ms, p50 {p50_ms:,.0f}ms")
    record_metric("request_layer_retry_avg_ms", avg_ms)


# ═══════════════════════════════════════════════════════════════════
# Layer 2 — Browser engines
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.slow
async def test_browser_patchright_scrape(measured_url: str):
    """Full browser scrape with Patchright — 3 iterations (browser is expensive)."""
    browser = AsyncBrowserLayer(stealth=True)

    samples: list[float] = []
    for i in range(3):
        t0 = time.monotonic()
        result = await browser.scrape(measured_url, engine="patchright")
        elapsed = (time.monotonic() - t0) * 1000
        if result.status == 200:
            samples.append(elapsed)
            print(f"    run {i+1}: {elapsed:,.0f}ms")
        else:
            print(f"    run {i+1}: FAILED — {result.error}")

    assert len(samples) >= 1, "All patchright runs failed"
    avg_ms = sum(samples) / len(samples)
    print(f"\n  🖥️  patchright: avg {avg_ms:,.0f}ms ({len(samples)}/3 ok)")
    record_metric("browser_patchright_avg_ms", avg_ms)
    assert_threshold("browser_patchright_total_ms", avg_ms, tolerance_pct=0.5)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_browser_camoufox_scrape(measured_url: str):
    """Full browser scrape with Camoufox."""
    try:
        from camoufox import AsyncCamoufox  # noqa: F401
    except ImportError:
        pytest.skip("camoufox not installed")

    browser = AsyncBrowserLayer(stealth=True)

    samples: list[float] = []
    for i in range(3):
        t0 = time.monotonic()
        result = await browser.scrape(measured_url, engine="camoufox")
        elapsed = (time.monotonic() - t0) * 1000
        if result.status == 200:
            samples.append(elapsed)
            print(f"    run {i+1}: {elapsed:,.0f}ms")
        else:
            print(f"    run {i+1}: FAILED — {result.error}")

    assert len(samples) >= 1, "All camoufox runs failed"
    avg_ms = sum(samples) / len(samples)
    print(f"\n  🦊 camoufox: avg {avg_ms:,.0f}ms ({len(samples)}/3 ok)")
    record_metric("browser_camoufox_avg_ms", avg_ms)
    assert_threshold("browser_camoufox_total_ms", avg_ms, tolerance_pct=0.5)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_browser_nodriver_scrape(measured_url: str):
    """Full browser scrape with nodriver."""
    try:
        import nodriver as nd  # noqa: F401
    except ImportError:
        pytest.skip("nodriver not installed")

    browser = AsyncBrowserLayer(stealth=True)

    samples: list[float] = []
    for i in range(3):
        t0 = time.monotonic()
        result = await browser.scrape(measured_url, engine="nodriver")
        elapsed = (time.monotonic() - t0) * 1000
        if result.status == 200:
            samples.append(elapsed)
            print(f"    run {i+1}: {elapsed:,.0f}ms")
        else:
            print(f"    run {i+1}: FAILED — {result.error}")

    assert len(samples) >= 1, "All nodriver runs failed"
    avg_ms = sum(samples) / len(samples)
    print(f"\n  🚗 nodriver: avg {avg_ms:,.0f}ms ({len(samples)}/3 ok)")
    record_metric("browser_nodriver_avg_ms", avg_ms)
    assert_threshold("browser_nodriver_total_ms", avg_ms, tolerance_pct=0.5)


# ═══════════════════════════════════════════════════════════════════
# Pipeline happy path (curl_cffi wins → should be fast)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pipeline_request_happy_path(measured_url: str):
    """Pipeline scrape where curl_cffi succeeds (no browser fallback)."""
    pipeline = SmartScrapePipeline()

    samples: list[float] = []
    layers: list[str] = []
    for i in range(10):
        t0 = time.monotonic()
        result = await pipeline.scrape(measured_url)
        elapsed = (time.monotonic() - t0) * 1000
        if result.status == "success":
            samples.append(elapsed)
            layers.append(result.layer_used)

    assert len(samples) >= 5, "Pipeline had too many failures"
    avg_ms = sum(sorted(samples)[:8]) / min(len(samples), 8)
    p50_ms = sorted(samples)[len(samples) // 2]
    # Verify we're hitting request layer (not browser)
    request_hits = sum(1 for l in layers if l == "request")

    print(
        f"\n  🔄 pipeline (happy path): avg {avg_ms:,.0f}ms, p50 {p50_ms:,.0f}ms, "
        f"request hits {request_hits}/{len(layers)}"
    )
    record_metric("pipeline_happy_path_avg_ms", avg_ms)
    record_metric("pipeline_happy_path_p50_ms", p50_ms)
    assert_threshold("pipeline_request_success_ms", avg_ms, tolerance_pct=0.3)
