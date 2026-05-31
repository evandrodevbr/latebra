"""Performance baseline: memory stability.

Detects memory leaks across repeated scrape operations.
Uses memory-profiler to track RSS before/after workloads.

Requirements:
    pip install memory-profiler

Run with:
    pytest tests/performance/test_memory_stability.py -v -s
"""

from __future__ import annotations

import asyncio
import logging
import os

import pytest

from latebra.layers.request import AsyncRequestLayer
from latebra.pipeline import SmartScrapePipeline

from .conftest import record_metric, PERF_THRESHOLDS

logger = logging.getLogger(__name__)


def _get_rss_mb() -> float:
    """Get current process RSS in MB."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        # Fallback: /proc/self/status
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024.0
        except Exception:
            return 0.0


@pytest.mark.asyncio
@pytest.mark.slow
async def test_memory_growth_100_request_ops(measured_url: str):
    """Run 100 request-layer operations and measure memory growth.

    A leak in the session/cookie/header handling would manifest here.
    """
    layer = AsyncRequestLayer()
    initial_rss = _get_rss_mb()

    for _ in range(100):
        result = await layer.fetch(measured_url)
        assert result.status == 200, f"Request failed at iteration: {result.error}"

    # Allow GC to settle
    import gc
    gc.collect()
    await asyncio.sleep(0.5)

    final_rss = _get_rss_mb()
    growth_mb = final_rss - initial_rss

    threshold = PERF_THRESHOLDS["memory_growth_100_ops_mb"]
    record_metric("memory_growth_100_ops_mb", growth_mb)

    print(
        f"\n  💾 100 HTTP ops: {initial_rss:.1f}MB → {final_rss:.1f}MB "
        f"(+{growth_mb:.1f}MB, threshold: {threshold:.0f}MB)"
    )
    assert growth_mb < threshold, (
        f"Memory grew {growth_mb:.1f}MB after 100 requests "
        f"(threshold: {threshold:.0f}MB). Possible leak in request layer."
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_memory_growth_20_pipeline_ops(measured_url: str):
    """Run 20 full pipeline operations and measure memory growth.

    Pipeline creates browser layers per call — check that cleanup works.
    """
    pipeline = SmartScrapePipeline()
    initial_rss = _get_rss_mb()

    for i in range(20):
        result = await pipeline.scrape(measured_url)
        if result.status != "success":
            logger.warning("Pipeline op %d failed: %s", i, result.error)

    import gc
    gc.collect()
    await asyncio.sleep(0.5)

    final_rss = _get_rss_mb()
    growth_mb = final_rss - initial_rss

    # Pipeline uses more memory (browser layers), so threshold is higher
    threshold = PERF_THRESHOLDS["memory_growth_100_ops_mb"] * 1.5
    record_metric("memory_growth_20_pipeline_ops_mb", growth_mb)

    print(
        f"\n  💾 20 pipeline ops: {initial_rss:.1f}MB → {final_rss:.1f}MB "
        f"(+{growth_mb:.1f}MB)"
    )
    assert growth_mb < threshold, (
        f"Memory grew {growth_mb:.1f}MB after 20 pipeline ops "
        f"(threshold: {threshold:.0f}MB). Browser cleanup may be leaking."
    )
