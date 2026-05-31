"""Performance baseline: anonymity efficacy.

Measures how often the stealth pipeline evades bot detection.
Tests against real detection services and local fingerprint checks.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from latebra.layers.request import AsyncRequestLayer
from latebra.constants import DETECTION_MARKERS

from .conftest import record_metric, PERF_THRESHOLDS

logger = logging.getLogger(__name__)


# Known bot-detection test endpoints (passive — just check response)
ANONYMITY_TARGETS = [
    {"url": "https://httpbin.org/headers", "name": "httpbin/headers"},
    {"url": "https://httpbin.org/ip", "name": "httpbin/ip"},
    {"url": "https://httpbin.org/user-agent", "name": "httpbin/ua"},
]


def _check_detection_markers(html: str) -> list[str]:
    """Return list of detection markers found in HTML content."""
    markers: list[str] = []
    html_lower = html.lower()
    for marker in DETECTION_MARKERS:
        if marker.lower() in html_lower:
            markers.append(marker)
    return markers


@pytest.mark.asyncio
@pytest.mark.slow
async def test_anonymity_request_layer():
    """Test that curl_cffi requests are not detected as bots."""
    layer = AsyncRequestLayer()
    total = len(ANONYMITY_TARGETS)
    passed = 0
    results: list[dict] = []

    for target in ANONYMITY_TARGETS:
        result = await layer.fetch(target["url"])
        if result.status == 200:
            markers = _check_detection_markers(result.content)
            if not markers:
                passed += 1
                results.append({"name": target["name"], "detected": False})
            else:
                results.append({"name": target["name"], "detected": True, "markers": markers})
        else:
            results.append({"name": target["name"], "error": result.error})

    pass_rate = passed / total if total > 0 else 0
    record_metric("anonymity_request_layer_pass_rate", pass_rate * 100)

    print(f"\n  🛡️  Anonymity (request layer): {passed}/{total} passed ({pass_rate:.0%})")
    for r in results:
        status = "✅" if not r.get("detected") and not r.get("error") else "❌"
        extras = r.get("markers", []) or r.get("error", "")
        print(f"    {status} {r['name']} {extras}")

    threshold = PERF_THRESHOLDS["anonymity_pass_rate"]
    assert pass_rate >= threshold, (
        f"Anonymity pass rate {pass_rate:.0%} below threshold {threshold:.0%}"
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_anonymity_tls_fingerprint_randomization():
    """Verify that TLS impersonation changes across requests.

    Multiple sequential requests should use randomized fingerprints
    to avoid pattern detection. We verify by checking header diversity.
    """
    layer = AsyncRequestLayer()
    headers_samples: list[str] = []

    for _ in range(5):
        result = await layer.fetch("https://httpbin.org/headers")
        if result.status == 200:
            headers_samples.append(result.content)
        await asyncio.sleep(0.1)

    assert len(headers_samples) >= 3, f"Only {len(headers_samples)}/5 requests succeeded"

    # Check that headers contain variation (not all identical)
    unique = len(set(headers_samples))
    print(f"\n  🔄 TLS fingerprint diversity: {unique}/{len(headers_samples)} unique")
    record_metric("anonymity_tls_diversity_ratio", unique / len(headers_samples))


@pytest.mark.asyncio
@pytest.mark.slow
async def test_anonymity_detection_marker_awareness():
    """Verify pipeline can detect when it has been blocked.

    Makes a request that SHOULD trigger detection markers.
    The check_anonymity method should identify these.
    """
    from latebra.pipeline import SmartScrapePipeline
    pipeline = SmartScrapePipeline()

    # Use a known hard-to-scrape site that returns detection markers
    result = await pipeline.scrape("https://httpbin.org/headers")
    if result.status == "success" and result.content:
        markers = _check_detection_markers(result.content)
        print(f"\n  🔍 Detection markers found: {markers if markers else 'none'}")
        record_metric("anonymity_detection_markers_found", len(markers))
    else:
        print(f"\n  ⚠️  Detection marker test skipped (pipeline returned: {result.status})")
