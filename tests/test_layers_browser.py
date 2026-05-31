"""Tests for the browser automation layer."""

from __future__ import annotations

import pytest

from latebra.layers.browser import AsyncBrowserLayer, BrowserResult


class TestBrowserResult:
    """Test the BrowserResult dataclass."""

    def test_default_values(self):
        r = BrowserResult()
        assert r.html == ""
        assert r.url == ""
        assert r.status == 0
        assert r.engine == ""
        assert r.error is None
        assert r.timing_ms == 0.0
        assert r.screenshot is None


class TestAsyncBrowserLayer:
    """Test AsyncBrowserLayer configuration."""

    def test_init_default(self):
        layer = AsyncBrowserLayer()
        assert layer.stealth is True

    def test_init_stealth_off(self):
        layer = AsyncBrowserLayer(stealth=False)
        assert layer.stealth is False

    def test_engines_chain(self):
        assert AsyncBrowserLayer.ENGINES == ["patchright", "camoufox", "nodriver"]

    def test_viewports(self):
        vp = AsyncBrowserLayer.VIEWPORTS
        assert (1920, 1080) in vp
        assert len(vp) >= 5

    def test_scrape_no_browser(self):
        """Scrape should fail gracefully without browser installed."""
        import asyncio

        layer = AsyncBrowserLayer()
        result = asyncio.run(layer.scrape("http://example.com"))
        assert result.error is not None
        assert result.status == 0
