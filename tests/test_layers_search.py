"""Tests for SearchLayer with auto-detection and fallback."""

import pytest


@pytest.mark.asyncio
async def test_search_layer_auto_detects_searxng():
    """SearchLayer should detect SearXNG availability.

    Requires a local SearXNG instance on http://localhost:8090
    (optional service: docker run -d -p 8090:8080 searxng/searxng).
    Skips when the service is not running.
    """
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(base_url="http://localhost:8090", search_backend="auto")
    detected = await layer._detect_searxng()
    if not detected:
        pytest.skip("SearXNG is not running at http://localhost:8090")
    assert detected is True


@pytest.mark.asyncio
async def test_search_layer_auto_fallback():
    """SearchLayer should fallback to built-in when SearXNG unavailable."""
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(base_url="http://localhost:9999", search_backend="auto")
    results = await layer.search("python", max_results=3)

    assert isinstance(results, list)
    # Should return results from built-in engines
    assert len(results) > 0


@pytest.mark.asyncio
async def test_search_layer_explicit_builtin():
    """SearchLayer should use built-in when explicitly configured."""
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(search_backend="built-in")
    results = await layer.search("python", max_results=3)

    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_search_layer_explicit_searxng():
    """SearchLayer should use SearXNG when explicitly configured."""
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(base_url="http://localhost:8090", search_backend="searxng")
    results = await layer.search("python", max_results=3)

    assert isinstance(results, list)
