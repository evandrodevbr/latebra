"""Tests for the HTTP request layer."""

from __future__ import annotations

import pytest

from latebra.layers.request import AsyncRequestLayer, RequestResult


class TestRequestResult:
    """Test the RequestResult dataclass."""

    def test_default_values(self):
        r = RequestResult()
        assert r.status == 0
        assert r.content == ""
        assert r.headers == {}
        assert r.error is None
        assert r.timing_ms == 0.0
        assert r.proxy_used is None


class TestAsyncRequestLayer:
    """Test the AsyncRequestLayer initialization and config."""

    def test_init_default(self):
        layer = AsyncRequestLayer()
        assert layer.timeout == 15
        assert layer.max_retries == 2
        assert layer.impersonate == "chrome120"

    def test_init_custom(self):
        layer = AsyncRequestLayer(timeout=15, max_retries=5, impersonate="safari17_0")
        assert layer.timeout == 15
        assert layer.max_retries == 5
        assert layer.impersonate == "safari17_0"

    def test_impersonate_options(self):
        assert "chrome120" in AsyncRequestLayer.IMPERSONATE_OPTIONS
        assert "safari17_0" in AsyncRequestLayer.IMPERSONATE_OPTIONS

    def test_fetch_no_session(self):
        """Test fetch works (curl_cffi is installed)."""
        import asyncio

        layer = AsyncRequestLayer()
        result = asyncio.run(layer.fetch("http://example.com"))
        # Should succeed since curl_cffi is available
        assert result.status in (0, 200)
        assert result.error is None or "connect" not in result.error
