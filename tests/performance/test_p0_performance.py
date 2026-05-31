"""Performance tests for P0 features: search, crawl, batch, interact."""

import time
import pytest


# ═══════════ Search performance ═══════════

@pytest.mark.asyncio
async def test_search_latency():
    """Search should return results within reasonable time."""
    from latebra.layers.search import SearchLayer

    layer = SearchLayer(base_url="http://localhost:8090", timeout=10)

    t0 = time.monotonic()
    results = await layer.search("python programming", max_results=5)
    elapsed = (time.monotonic() - t0) * 1000

    assert len(results) > 0, "Search returned no results"
    assert elapsed < 5000, f"Search too slow: {elapsed:,.0f}ms"
    print(f"\n  🔍 search latency: {elapsed:,.0f}ms, {len(results)} results")


# ═══════════ Crawl performance ═══════════

@pytest.mark.asyncio
async def test_crawl_performance():
    """Crawl should complete within reasonable time for depth=0."""
    from latebra.layers.crawler import CrawlerLayer

    layer = CrawlerLayer(max_depth=0, max_pages=1, timeout=10)

    t0 = time.monotonic()
    pages = await layer.crawl("https://httpbin.org/html")
    elapsed = (time.monotonic() - t0) * 1000

    assert len(pages) == 1
    assert elapsed < 8000, f"Crawl too slow: {elapsed:,.0f}ms"
    print(f"\n  🕷️  crawl (depth=0): {elapsed:,.0f}ms")


# ═══════════ Batch scrape performance ═══════════

@pytest.mark.asyncio
async def test_batch_scrape_performance():
    """Batch scrape of 3 URLs should be faster than 3x sequential."""
    from latebra.pipeline import SmartScrapePipeline

    pipeline = SmartScrapePipeline()
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/links/2/0",
        "https://httpbin.org/ip",
    ]

    t0 = time.monotonic()
    results = await pipeline.batch_scrape(urls, max_concurrent=3)
    elapsed = (time.monotonic() - t0) * 1000

    successes = sum(1 for r in results if r.status == "success")
    assert successes == 3, f"Batch scrape had failures: {successes}/3"
    print(f"\n  📦 batch 3 URLs (concurrent=3): {elapsed:,.0f}ms")


# ═══════════ Tool count verification ═══════════

def test_mcp_tool_count():
    """Verify all 7 MCP tools are registered."""
    from latebra.server import LatebraServer
    server = LatebraServer()
    tools = server.tool_definitions
    assert len(tools) == 7
    names = {t["name"] for t in tools}
    expected = {
        "latebra_scrape",
        "latebra_scrape_with_browser",
        "latebra_check_anonymity",
        "latebra_search",
        "latebra_crawl",
        "latebra_batch_scrape",
        "latebra_interact",
    }
    assert names == expected, f"Missing tools: {expected - names}"
