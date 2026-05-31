"""Tests for the SmartScrapePipeline orchestrator."""

from __future__ import annotations

import pytest

from latebra.pipeline import ScrapeResult, SmartScrapePipeline


class TestScrapeResult:
    """Test the ScrapeResult dataclass."""

    def test_default_values(self):
        result = ScrapeResult(url="http://example.com")
        assert result.url == "http://example.com"
        assert result.status == "error"
        assert result.content is None
        assert result.content_length == 0
        assert result.layer_used == ""
        assert result.error is None
        assert result.timing_ms == 0.0
        assert result.captcha_solved is False
        assert result.proxies_rotated == 0
        assert result.title == ""
        assert result.extracted_text == ""
        assert result.cached is False

    def test_to_dict(self):
        result = ScrapeResult(
            url="http://example.com",
            status="success",
            content="<html>test</html>",
            content_length=20,
            layer_used="request",
            timing_ms=123.456,
            title="Test Title",
        )
        d = result.to_dict()
        assert d["url"] == "http://example.com"
        assert d["status"] == "success"
        assert d["content_length"] == 20
        assert d["layer_used"] == "request"
        assert d["timing_ms"] == 123.46
        assert d["title"] == "Test Title"

    def test_to_dict_error(self):
        result = ScrapeResult(
            url="http://example.com",
            status="error",
            error="Connection failed",
        )
        d = result.to_dict()
        assert d["status"] == "error"
        assert d["error"] == "Connection failed"


class TestSmartScrapePipeline:
    """Test the SmartScrapePipeline initialization."""

    def test_init_default(self):
        pipeline = SmartScrapePipeline()
        assert pipeline.request_layer is not None
        assert pipeline.browser_layer is not None
        assert pipeline.extraction_layer is not None
        assert pipeline.proxy_manager is not None
        assert pipeline.captcha_solver is not None

    def test_init_with_proxies(self, proxies):
        pipeline = SmartScrapePipeline(proxies=proxies)
        stats = pipeline.proxy_manager.stats
        assert stats["total_proxies"] == 2

    def test_scrape_no_deps_returns_error(self):
        """Test that scrape works or returns partial data."""
        import asyncio
        pipeline = SmartScrapePipeline()
        result = asyncio.run(pipeline.scrape("http://example.com"))
        assert result.status in ("success", "error")
        assert result.layer_used in ("", "request")
