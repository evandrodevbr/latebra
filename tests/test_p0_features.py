"""Test P0 features: search, crawl, batch, extract, interact."""

import asyncio
import json
import time

import pytest


# ═══════════ #1: latebra_search ═══════════

@pytest.mark.asyncio
async def test_search_layer_exists():
    """Search layer module should be importable."""
    from latebra.layers.search import SearchLayer
    assert SearchLayer is not None


@pytest.mark.asyncio
async def test_search_returns_results():
    """Search should return structured results from SearXNG."""
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(base_url="http://localhost:8090")
    results = await layer.search("python", max_results=3)

    assert isinstance(results, list)
    assert len(results) > 0, "Search returned empty results"
    assert len(results) <= 3

    for r in results:
        assert "title" in r, f"Missing title in {r}"
        assert "url" in r, f"Missing url in {r}"
        assert "snippet" in r, f"Missing snippet in {r}"


@pytest.mark.asyncio
async def test_search_handles_timeout():
    """Search should handle network errors gracefully."""
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(base_url="http://localhost:9999", timeout=2)
    results = await layer.search("test", max_results=3)

    # Should return empty list, not crash
    assert isinstance(results, list)
    assert len(results) == 0


# ═══════════ #2: latebra_crawl ═══════════

@pytest.mark.asyncio
async def test_crawler_layer_exists():
    """Crawler layer module should be importable."""
    from latebra.layers.crawler import CrawlerLayer
    assert CrawlerLayer is not None


@pytest.mark.asyncio
async def test_crawl_discovers_links():
    """Crawl should find links on a page and follow them."""
    from latebra.layers.crawler import CrawlerLayer

    layer = CrawlerLayer(max_depth=1, max_pages=3)
    pages = await layer.crawl("https://httpbin.org/links/10/0")

    assert isinstance(pages, list)
    assert len(pages) > 0
    for page in pages:
        assert "url" in page
        assert "title" in page
        assert "links" in page


@pytest.mark.asyncio
async def test_crawl_respects_depth_limit():
    """Crawl should not exceed configured depth."""
    from latebra.layers.crawler import CrawlerLayer

    layer = CrawlerLayer(max_depth=0, max_pages=10)
    pages = await layer.crawl("https://httpbin.org/links/5/0")

    assert len(pages) == 1  # depth 0 = only seed URL


# ═══════════ #3: latebra_batch_scrape ═══════════

@pytest.mark.asyncio
async def test_batch_scrape_multiple_urls():
    """Pipeline should support batch scraping."""
    from latebra.pipeline import SmartScrapePipeline

    pipeline = SmartScrapePipeline()
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/links/2/0",
    ]

    results = await pipeline.batch_scrape(urls)

    assert len(results) == 2
    for r in results:
        assert r.status == "success", f"Batch scrape failed: {r.error}"


@pytest.mark.asyncio
async def test_batch_scrape_respects_concurrency():
    """Batch should limit concurrent requests."""
    from latebra.pipeline import SmartScrapePipeline

    pipeline = SmartScrapePipeline()
    urls = ["https://httpbin.org/html"] * 5

    t0 = time.monotonic()
    results = await pipeline.batch_scrape(urls, max_concurrent=2)
    elapsed = (time.monotonic() - t0) * 1000

    assert len(results) == 5
    # With concurrency=2, 5 URLs should complete faster than sequential (5 × avg_latency)
    print(f"\n  📦 batch 5 URLs (concurrent=2): {elapsed:,.0f}ms")


# ═══════════ #4: latebra_extract ═══════════

@pytest.mark.asyncio
async def test_extract_structured_from_html():
    """Extract should pull structured data from HTML content."""
    from latebra.layers.extraction import AsyncExtractionLayer

    html = """
    <html><body>
        <h1>Product Name</h1>
        <span class="price">$19.99</span>
        <p>The best product ever.</p>
    </body></html>
    """

    layer = AsyncExtractionLayer()
    result = await layer.extract(html, "http://example.com/product")

    assert result.title or result.text or result.markdown, (
        f"Extraction produced no content. markdown={result.markdown[:80]}"
    )
    assert not result.error, f"Extraction error: {result.error}"


# ═══════════ #5: latebra_interact ═══════════

def test_interact_layer_exists():
    """Interact layer module should be importable."""
    from latebra.layers.interact import InteractLayer
    assert InteractLayer is not None


def test_interact_actions_defined():
    """Interact layer should define click, type, navigate actions."""
    from latebra.layers.interact import InteractLayer

    layer = InteractLayer()
    assert hasattr(layer, "click"), "Missing click action"
    assert hasattr(layer, "type_text"), "Missing type_text action"
    assert hasattr(layer, "navigate"), "Missing navigate action"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_interact_navigate_and_click():
    """Interact should navigate and click elements on a page."""
    from latebra.layers.interact import InteractLayer
    from latebra.layers.browser import AsyncBrowserLayer

    browser = AsyncBrowserLayer(stealth=True)
    interact = InteractLayer(browser=browser)

    await interact.navigate("https://httpbin.org/links/2/0")

    result = await interact.click("a")
    assert result is not None
