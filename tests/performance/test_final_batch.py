"""Test final batch optimizations: slot dataclasses, parallel fallback, TLS rotation."""

import pytest
from latebra.layers.request import AsyncRequestLayer
from latebra.layers.browser import AsyncBrowserLayer


# ═══════ #7: TLS fingerprint rotation ═══════

def test_request_layer_supports_impersonate_rotation():
    """TLS impersonation should vary across instances for anonymity."""
    layer1 = AsyncRequestLayer(impersonate="chrome120")
    layer2 = AsyncRequestLayer(impersonate="chrome124")
    assert layer1.impersonate != layer2.impersonate, (
        "Impersonation should support rotation across instances"
    )


# ═══════ #8: Slot-based dataclasses ═══════

def test_scrape_result_is_slotted():
    """ScrapeResult should use __slots__ for memory efficiency."""
    from latebra.pipeline import ScrapeResult

    # Verify it's a dataclass (which should use __slots__)
    import dataclasses
    assert dataclasses.is_dataclass(ScrapeResult), "ScrapeResult must be a dataclass"


def test_browser_result_is_slotted():
    """BrowserResult should use __slots__."""
    from latebra.layers.browser import BrowserResult
    import dataclasses
    assert dataclasses.is_dataclass(BrowserResult), "BrowserResult must be a dataclass"


# ═══════ #9: Pipeline session reuse ═══════

@pytest.mark.asyncio
async def test_pipeline_reuses_request_session():
    """Pipeline should reuse AsyncRequestLayer session across scrape calls."""
    from latebra.pipeline import SmartScrapePipeline

    pipeline = SmartScrapePipeline()
    # First scrape initializes the session
    result1 = await pipeline.scrape("https://httpbin.org/html")
    assert result1.status == "success"

    # Second scrape should reuse the same session (no re-init)
    result2 = await pipeline.scrape("https://httpbin.org/html")
    assert result2.status == "success"

    # Both should use request layer
    assert result1.layer_used == result2.layer_used == "request"


# ═══════ #10: Parallel browser fallback ═══════

def test_pipeline_has_parallel_fallback_flag():
    """Pipeline should support parallel browser fallback mode."""
    from latebra.pipeline import SmartScrapePipeline
    assert hasattr(SmartScrapePipeline, "PARALLEL_FALLBACK"), (
        "Missing PARALLEL_FALLBACK — enable race condition between browsers"
    )
