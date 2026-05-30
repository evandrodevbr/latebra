"""Tests for the latebra pipeline orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from latebra.pipeline import ScrapeResult, SmartScrapePipeline


class TestScrapeResult:
    """Test the ScrapeResult dataclass."""

    def test_default_values(self) -> None:
        result = ScrapeResult(url="https://example.com", status="success")
        assert result.url == "https://example.com"
        assert result.status == "success"
        assert result.content is None
        assert result.content_length == 0
        assert result.layer_used == ""
        assert result.error is None
        assert result.timing_ms == 0.0
        assert result.captcha_solved is False
        assert result.proxies_rotated == 0

    def test_to_dict(self) -> None:
        result = ScrapeResult(
            url="https://example.com",
            status="success",
            content="<html>content</html>",
            content_length=20,
            layer_used="request",
            timing_ms=1500.567,
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com"
        assert d["status"] == "success"
        assert d["content_length"] == 20
        assert d["layer_used"] == "request"
        assert d["timing_ms"] == 1500.57
        assert "content" not in d  # content not in dict output


class TestSmartScrapePipeline:
    """Test the SmartScrapePipeline orchestrator."""

    @pytest.mark.asyncio
    async def test_scrape_fallback_chain(self) -> None:
        """Pipeline should try all layers and return last result on total failure."""
        pipeline = SmartScrapePipeline()

        # Mock curl_cffi to fail
        with patch.object(pipeline, "_try_request_layer", new=AsyncMock(return_value=ScrapeResult(
            url="https://example.com", status="blocked", layer_used="request",
            error="Blocked by WAF",
        ))):
            # Mock browser layers to also fail
            with patch.object(pipeline, "_try_browser_layer", new=AsyncMock(return_value=ScrapeResult(
                url="https://example.com", status="error", layer_used="browser_nodriver",
                error="nodriver failed",
            ))):
                result = await pipeline.scrape("https://example.com")
                assert result.status == "error"
                assert "nodriver" in result.layer_used

    @pytest.mark.asyncio
    async def test_scrape_success_first_layer(self) -> None:
        """Pipeline should stop at first successful layer."""
        pipeline = SmartScrapePipeline()

        success_result = ScrapeResult(
            url="https://example.com",
            status="success",
            content="<html>full content</html>",
            content_length=22,
            layer_used="request",
        )

        with patch.object(pipeline, "_try_request_layer", new=AsyncMock(return_value=success_result)):
            result = await pipeline.scrape("https://example.com")
            assert result.status == "success"
            assert result.layer_used == "request"

    @pytest.mark.asyncio
    async def test_scrape_with_browser(self) -> None:
        """Should dispatch to the correct browser engine."""
        pipeline = SmartScrapePipeline()

        mock_result = ScrapeResult(
            url="https://example.com",
            status="success",
            content="<html>browser content</html>",
            content_length=26,
            layer_used="browser_patchright",
        )

        with patch.object(pipeline, "_try_browser_layer", new=AsyncMock(return_value=mock_result)) as mock_browser:
            result = await pipeline.scrape_with_browser("https://example.com", browser="patchright")
            mock_browser.assert_called_once_with("https://example.com", engine="patchright")
            assert result.status == "success"
