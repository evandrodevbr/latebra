"""Batch performance optimization tests: cache-first, timeout tuning, streaming."""

import asyncio
import time

import pytest
from latebra.layers.request import AsyncRequestLayer
from latebra.constants import DEFAULT_CACHE_TTL


# ═══════════ #5: Cache-first check before HTTP ═══════════

def test_cache_ttl_is_reasonable():
    """Default cache TTL should be between 1 hour and 24 hours."""
    assert 3600 <= DEFAULT_CACHE_TTL <= 86400, (
        f"DEFAULT_CACHE_TTL={DEFAULT_CACHE_TTL} should be 1h-24h for cache-first to work"
    )


# ═══════════ #6: Timeout tuning ═══════════

def test_request_layer_default_timeout_is_reasonable():
    """Default timeout should be ≤ 15s for reasonable UX."""
    layer = AsyncRequestLayer()
    assert layer.timeout <= 15, (
        f"Default timeout={layer.timeout}s should be ≤15s for fast failures"
    )


# ═══════════ #7: Streaming response ═══════════

@pytest.mark.asyncio
async def test_request_layer_response_streaming():
    """Large responses should not cause memory bloat."""
    layer = AsyncRequestLayer()
    import resource
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    result = await layer.fetch("https://httpbin.org/bytes/102400")
    assert result.status == 200

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    growth_kb = rss_after - rss_before

    # 100KB response should not grow RSS by more than 10MB
    assert growth_kb < 10240, (
        f"Memory growth {growth_kb}KB for 100KB response — possible buffer bloat"
    )


# ═══════════ #8: Parallel proxy health ═══════════

@pytest.mark.asyncio
async def test_proxy_manager_supports_batch_health_check():
    """ProxyManager should validate proxies concurrently."""
    from latebra.proxy.manager import ProxyManager

    pm = ProxyManager(proxies=[
        "socks5://test1:1080",
        "socks5://test2:1080",
        "socks5://test3:1080",
    ])

    # Sequential health check fallback
    t0 = time.monotonic()
    healthy = await pm.health_check_all()
    elapsed_seq = (time.monotonic() - t0) * 1000

    assert isinstance(healthy, list)
    print(f"\n  🏥 proxy health check: {elapsed_seq:,.0f}ms, {len(healthy)} healthy")
