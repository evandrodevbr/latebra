"""Performance baseline: MCP server throughput.

Measures concurrent request handling capacity of the latebra MCP server.
Uses asyncio.gather to simulate multiple simultaneous clients.

NOTE: These tests require the MCP server to be running.
Run: `python -m latebra run` in another terminal before executing.
"""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from latebra.pipeline import SmartScrapePipeline

from .conftest import record_metric

logger = logging.getLogger(__name__)


async def _timed_scrape(pipeline: SmartScrapePipeline, url: str) -> dict:
    """Run a single scrape and return timing + status."""
    t0 = time.monotonic()
    result = await pipeline.scrape(url)
    elapsed = (time.monotonic() - t0) * 1000
    return {
        "url": url,
        "status": result.status,
        "layer": result.layer_used,
        "timing_ms": elapsed,
        "error": result.error,
    }


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="concurrent")
async def test_concurrent_2_clients(measured_url: str, benchmark):
    """2 concurrent scrape requests."""
    pipeline = SmartScrapePipeline()

    async def _concurrent():
        tasks = [_timed_scrape(pipeline, measured_url) for _ in range(2)]
        return await asyncio.gather(*tasks)

    results = await benchmark(_concurrent)
    successes = [r for r in results if r["status"] == "success"]
    assert len(successes) == 2, f"Only {len(successes)}/2 succeeded: {results}"
    avg_ms = sum(r["timing_ms"] for r in results) / len(results)
    record_metric("concurrent_2_avg_ms", avg_ms)
    print(f"\n  ⚡ 2 concurrent: avg {avg_ms:,.0f}ms per request")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="concurrent")
async def test_concurrent_5_clients(measured_url: str, benchmark):
    """5 concurrent scrape requests — stress test."""
    pipeline = SmartScrapePipeline()

    async def _concurrent():
        tasks = [_timed_scrape(pipeline, measured_url) for _ in range(5)]
        return await asyncio.gather(*tasks)

    results = await benchmark(_concurrent)
    successes = [r for r in results if r["status"] == "success"]
    failure_rate = (5 - len(successes)) / 5
    # Allow up to 40% failure under load (proxy exhaustion, rate limiting)
    assert failure_rate <= 0.40, f"Too many failures: {len(successes)}/5"
    avg_ms = sum(r["timing_ms"] for r in results) / len(results)
    record_metric("concurrent_5_avg_ms", avg_ms)
    print(f"\n  ⚡ 5 concurrent: avg {avg_ms:,.0f}ms, {len(successes)}/5 success")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="concurrent")
async def test_concurrent_10_clients(measured_url: str, benchmark):
    """10 concurrent scrape requests — load test."""
    pipeline = SmartScrapePipeline()

    async def _concurrent():
        tasks = [_timed_scrape(pipeline, measured_url) for _ in range(10)]
        return await asyncio.gather(*tasks)

    results = await benchmark(_concurrent)
    successes = [r for r in results if r["status"] == "success"]
    failure_rate = (10 - len(successes)) / 10
    assert failure_rate <= 0.50, f"Too many failures: {len(successes)}/10"
    avg_ms = sum(r["timing_ms"] for r in results) / len(results)
    record_metric("concurrent_10_avg_ms", avg_ms)
    total_time = max(r["timing_ms"] for r in results)
    record_metric("concurrent_10_total_ms", total_time)
    print(
        f"\n  ⚡ 10 concurrent: avg {avg_ms:,.0f}ms, "
        f"total {total_time:,.0f}ms, "
        f"{len(successes)}/10 success"
    )
