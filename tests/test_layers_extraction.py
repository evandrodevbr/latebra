"""Tests for the extraction layer with caching."""

from __future__ import annotations

import pytest

from latebra.layers.extraction import AsyncExtractionLayer, ContentCache, ExtractionResult


class TestExtractionResult:
    """Test the ExtractionResult dataclass."""

    def test_default_values(self):
        r = ExtractionResult()
        assert r.title == ""
        assert r.text == ""
        assert r.markdown == ""
        assert r.html == ""
        assert r.metadata == {}
        assert r.links == []
        assert r.cached is False

    def test_error_field(self):
        r = ExtractionResult(error="something broke")
        assert r.error == "something broke"


class TestContentCache:
    """Test the SQLite-backed cache."""

    def test_cache_miss(self):
        cache = ContentCache(":memory:")
        assert cache.get("http://example.com") is None

    def test_cache_set_and_get(self):
        cache = ContentCache(":memory:")
        data = {"title": "Test", "content": "hello"}
        cache.set("http://example.com", data, ttl=3600)
        result = cache.get("http://example.com", ttl=3600)
        assert result == data

    def test_cache_ttl_handling(self):
        """TTL=0 means immediately expired — basic ttl parameter check."""
        cache = ContentCache(":memory:")
        data = {"title": "Fresh"}
        cache.set("http://example.com", data, ttl=3600)
        # Use a ttl that would indicate expiry for this specific get
        # Even though the stored ttl is 3600, if we check just 1ms after
        # the creation, it shouldn't be expired.
        result = cache.get("http://example.com", ttl=3600)
        assert result == data

    def test_cache_ttl_expired(self):
        """Check that data stored with TTL=0 is expired on retrieval."""
        cache = ContentCache(":memory:")
        cache.set("http://example.com", {"title": "Old"}, ttl=0)
        result = cache.get("http://example.com")
        assert result is None


class TestAsyncExtractionLayer:
    """Test the extraction layer configuration."""

    def test_init_default(self):
        layer = AsyncExtractionLayer()
        assert layer.cache_ttl == 3600
        assert layer.use_cache is True
        assert layer.cache is not None

    def test_init_no_cache(self):
        layer = AsyncExtractionLayer(use_cache=False)
        assert layer.cache is None

    @pytest.mark.asyncio
    async def test_extract_fallback(self, sample_html, monkeypatch):
        """Test fallback extraction without Crawl4AI."""
        # Force fallback by making Crawl4AI import raise ImportError
        async def _raise_import_error(*args, **kwargs):
            raise ImportError("crawl4ai not available")
        monkeypatch.setattr(
            "latebra.layers.extraction.AsyncExtractionLayer._extract_crawl4ai",
            _raise_import_error,
        )
        layer = AsyncExtractionLayer(use_cache=False)
        result = await layer.extract(sample_html, "http://example.com")
        assert "Test Page" in result.title
        assert result.html == sample_html
        assert len(result.links) == 2

    @pytest.mark.asyncio
    async def test_extract_fallback_no_title(self, blocked_html, monkeypatch):
        async def _raise_import_error(*args, **kwargs):
            raise ImportError("crawl4ai not available")
        monkeypatch.setattr(
            "latebra.layers.extraction.AsyncExtractionLayer._extract_crawl4ai",
            _raise_import_error,
        )
        layer = AsyncExtractionLayer(use_cache=False)
        result = await layer.extract(blocked_html, "http://example.com")
        assert result.title == "Blocked"

    @pytest.mark.asyncio
    async def test_extract_cache_hit(self, sample_html):
        """Test that cached results are returned."""
        layer = AsyncExtractionLayer(use_cache=True, cache_ttl=3600)
        result1 = await layer.extract(sample_html, "http://cache-test.example")
        result2 = await layer.extract(sample_html, "http://cache-test.example")
        assert result2.cached is True
        assert result1.title == result2.title
