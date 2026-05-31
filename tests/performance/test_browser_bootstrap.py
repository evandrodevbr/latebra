"""Performance baseline: browser bootstrap time.

Measures browser launch overhead — the dominant cost in Layer 2.
Tracks both cold-start (first launch) and warm-start (subsequent navigations).
"""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from latebra.layers.browser import AsyncBrowserLayer

from .conftest import record_metric

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="browser_bootstrap")
async def test_patchright_cold_launch_first_navigation(measured_url: str, benchmark):
    """Cold browser launch + first navigation (no warmup)."""
    browser = AsyncBrowserLayer(stealth=True)

    async def _cold_scrape():
        return await browser.scrape(measured_url, engine="patchright")

    result = await benchmark(_cold_scrape)
    assert result.status == 200, f"Cold launch failed: {result.error}"
    record_metric("browser_cold_launch_ms", result.timing_ms)
    print(f"\n  🧊 patchright cold launch: {result.timing_ms:,.0f}ms")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="browser_bootstrap")
async def test_patchright_warm_navigation(measured_url: str, benchmark):
    """Warm browser — navigation on already-launched browser."""
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        async def _warm_nav():
            t0 = time.monotonic()
            await page.goto(measured_url, wait_until="domcontentloaded")
            content = await page.content()
            elapsed = (time.monotonic() - t0) * 1000
            return len(content), elapsed

        content_len, elapsed = await benchmark(_warm_nav)
        await browser.close()

    assert content_len > 0, "Empty page content"
    record_metric("browser_warm_navigation_ms", elapsed)
    print(f"\n  🔥 patchright warm navigation: {elapsed:,.0f}ms")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="browser_bootstrap")
async def test_camoufox_cold_launch(measured_url: str, benchmark):
    """Cold launch with Camoufox engine."""
    try:
        from camoufox import AsyncCamoufox
    except ImportError:
        pytest.skip("camoufox not installed")

    async def _cold_scrape():
        async with AsyncCamoufox(headless=True) as b:
            page = await b.new_page()
            await page.goto(measured_url, wait_until="domcontentloaded")
            return await page.content()

    content = await benchmark(_cold_scrape)
    assert len(content) > 0, "Empty content from Camoufox"


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.benchmark(group="browser_bootstrap")
async def test_nodriver_cold_launch(measured_url: str, benchmark):
    """Cold launch with nodriver engine."""
    try:
        import nodriver as nd
    except ImportError:
        pytest.skip("nodriver not installed")

    async def _cold_scrape():
        browser = await nd.start(headless=True)
        page = await browser.get(measured_url)
        await page.wait_for("body", timeout=15)
        content = await page.get_content()
        browser.stop()
        return len(content)

    content_len = await benchmark(_cold_scrape)
    assert content_len > 0, "Empty content from nodriver"
