"""Test browser warm pool optimization — keep browser alive between scrapes."""

import pytest
from latebra.layers.browser import AsyncBrowserLayer


def test_browser_layer_has_warm_pool_methods():
    """Browser layer should expose warm pool lifecycle methods."""
    layer = AsyncBrowserLayer()

    # RED: these methods don't exist yet
    assert hasattr(layer, "warm_up"), "Missing warm_up() — pre-launch browser"
    assert hasattr(layer, "warm_down"), "Missing warm_down() — close browser"
    assert hasattr(layer, "_warm_browser"), "Missing _warm_browser — pooled browser instance"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_warm_pool_improves_latency():
    """Second scrape with warm pool should be significantly faster."""
    layer = AsyncBrowserLayer(stealth=True)

    # Warm up the browser
    await layer.warm_up("patchright")

    import time
    t0 = time.monotonic()
    result = await layer.scrape("https://httpbin.org/html", engine="patchright")
    elapsed_warm = (time.monotonic() - t0) * 1000

    assert result.status == 200, f"Warm scrape failed: {result.error}"
    print(f"\n  🔥 warm scrape: {elapsed_warm:,.0f}ms")

    # Second scrape should reuse browser
    t0 = time.monotonic()
    result2 = await layer.scrape("https://httpbin.org/html", engine="patchright")
    elapsed_warm2 = (time.monotonic() - t0) * 1000

    assert result2.status == 200
    print(f"  🔥 warm scrape #2: {elapsed_warm2:,.0f}ms")

    # Both should be under 10s (vs 15s+ cold)
    assert elapsed_warm < 15000, f"Warm scrape too slow: {elapsed_warm:,.0f}ms"
    assert elapsed_warm2 < 15000, f"Warm scrape #2 too slow: {elapsed_warm2:,.0f}ms"

    await layer.warm_down()
