"""Tests for built-in search engines."""

import pytest


def test_base_search_engine_import():
    """BaseSearchEngine should be importable."""
    from latebra.layers.search_builtin import BaseSearchEngine
    assert BaseSearchEngine is not None


def test_base_search_engine_has_search_method():
    """BaseSearchEngine should define search method."""
    from latebra.layers.search_builtin import BaseSearchEngine
    assert hasattr(BaseSearchEngine, "search")


def test_base_search_engine_is_abstract():
    """BaseSearchEngine should not be instantiable directly."""
    from latebra.layers.search_builtin import BaseSearchEngine
    with pytest.raises(TypeError):
        BaseSearchEngine()


@pytest.mark.asyncio
async def test_duckduckgo_engine_import():
    """DuckDuckGoEngine should be importable."""
    from latebra.layers.search_builtin import DuckDuckGoEngine
    assert DuckDuckGoEngine is not None


@pytest.mark.asyncio
async def test_duckduckgo_engine_returns_results():
    """DuckDuckGo should return search results."""
    from latebra.layers.search_builtin import DuckDuckGoEngine

    engine = DuckDuckGoEngine()
    results = await engine.search("python programming", max_results=3)

    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3

    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert r["engine"] == "duckduckgo"


@pytest.mark.asyncio
async def test_duckduckgo_engine_handles_error():
    """DuckDuckGo should handle import errors gracefully."""
    from latebra.layers.search_builtin import DuckDuckGoEngine

    engine = DuckDuckGoEngine()
    # Test with mocked import failure
    import sys
    original_ddgs = sys.modules.get("ddgs")
    sys.modules["ddgs"] = None  # Force ImportError
    try:
        results = await engine.search("test", max_results=3)
        assert isinstance(results, list)
        assert len(results) == 0
    finally:
        if original_ddgs:
            sys.modules["ddgs"] = original_ddgs
        else:
            sys.modules.pop("ddgs", None)


@pytest.mark.asyncio
async def test_google_engine_import():
    """GoogleEngine should be importable."""
    from latebra.layers.search_builtin import GoogleEngine
    assert GoogleEngine is not None


@pytest.mark.asyncio
async def test_google_engine_returns_results():
    """Google should return search results."""
    from latebra.layers.search_builtin import GoogleEngine

    engine = GoogleEngine()
    results = await engine.search("python programming", max_results=3)

    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3

    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert r["engine"] == "google"


@pytest.mark.asyncio
async def test_bing_engine_import():
    """BingEngine should be importable."""
    from latebra.layers.search_builtin import BingEngine
    assert BingEngine is not None


@pytest.mark.asyncio
async def test_bing_engine_returns_results():
    """Bing should return search results."""
    from latebra.layers.search_builtin import BingEngine

    engine = BingEngine()
    results = await engine.search("python programming", max_results=3)

    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3

    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert r["engine"] == "bing"


@pytest.mark.asyncio
async def test_builtin_search_layer_exists():
    """BuiltInSearchLayer should be importable."""
    from latebra.layers.search_builtin import BuiltInSearchLayer
    assert BuiltInSearchLayer is not None


@pytest.mark.asyncio
async def test_builtin_search_layer_search():
    """BuiltInSearchLayer should search across multiple engines."""
    from latebra.layers.search_builtin import BuiltInSearchLayer

    layer = BuiltInSearchLayer()
    results = await layer.search("python programming", max_results=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 5

    # Check round-robin merge (different engines)
    engines = {r["engine"] for r in results}
    assert len(engines) > 1, "Should have results from multiple engines"


@pytest.mark.asyncio
async def test_builtin_search_layer_dedup():
    """BuiltInSearchLayer should deduplicate results by URL."""
    from latebra.layers.search_builtin import BuiltInSearchLayer

    layer = BuiltInSearchLayer()
    results = await layer.search("python", max_results=10)

    urls = [r["url"] for r in results]
    assert len(urls) == len(set(urls)), "Results should be deduplicated"
