"""Pipeline orchestrator for latebra anti-bot evasion.

Implements the 3-layer decision pipeline:
1. Request layer (curl_cffi) - fast, no JS
2. Browser layer (Patchright → Camoufox → nodriver)
3. Extraction layer (Crawl4AI)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from latebra.captcha.solver import CaptchaSolver
from latebra.constants import (
    DETECTION_MARKERS,
    MIN_CONTENT_LENGTH,
    PREVIEW_MAX_LENGTH,
)
from latebra.layers.browser import AsyncBrowserLayer
from latebra.layers.extraction import AsyncExtractionLayer
from latebra.layers.request import AsyncRequestLayer
from latebra.proxy.manager import ProxyManager
from latebra.validation import validate

logger = logging.getLogger(__name__)

# Terminal network errors that cannot be recovered by any layer
_TERMINAL_ERROR_PATTERNS: list[str] = [
    "ERR_NAME_NOT_RESOLVED",
    "Could not resolve host",
    "ERR_CONNECTION_REFUSED",
    "Connection refused",
    "ERR_ADDRESS_UNREACHABLE",
    "ERR_ADDRESS_INVALID",
    "No route to host",
    "getaddrinfo",
    "Name or service not known",
    "ERR_CONNECTION_CLOSED",
    "ERR_CONNECTION_RESET",
    "Connection reset",
    "Temporary failure in name resolution",
    "No address associated with hostname",
    "nodename nor servname",
]


def _is_terminal_error(error: str | None) -> bool:
    """Check if an error is terminal (unrecoverable across all layers)."""
    if not error:
        return False
    return any(pattern.lower() in error.lower() for pattern in _TERMINAL_ERROR_PATTERNS)


@dataclass
class ScrapeResult:
    """Result from the scraping pipeline."""
    url: str
    status: str = "error"  # "success", "blocked", "error"
    content: Optional[str] = None
    content_length: int = 0
    layer_used: str = ""
    error: Optional[str] = None
    timing_ms: float = 0.0
    captcha_solved: bool = False
    proxies_rotated: int = 0
    title: str = ""
    extracted_text: str = ""
    cached: bool = False

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "status": self.status,
            "content_length": self.content_length,
            "layer_used": self.layer_used,
            "error": self.error,
            "timing_ms": round(self.timing_ms, 2),
            "captcha_solved": self.captcha_solved,
            "proxies_rotated": self.proxies_rotated,
            "title": self.title,
            "cached": self.cached,
        }


class SmartScrapePipeline:
    """Orchestrates the multi-layer anti-bot evasion pipeline."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        two_captcha_key: str | None = None,
        capsolver_key: str | None = None,
    ) -> None:
        self.request_layer = AsyncRequestLayer()
        self.browser_layer = AsyncBrowserLayer(stealth=True)
        self.extraction_layer = AsyncExtractionLayer(use_cache=True)
        self.proxy_manager = ProxyManager(proxies=proxies or [])
        self.captcha_solver = CaptchaSolver(
            two_captcha_key=two_captcha_key,
            capsolver_key=capsolver_key,
        )

    async def _build_success_result(
        self, url: str, content: str, layer: str, start: float,
    ) -> ScrapeResult:
        """Build a success result with extraction applied."""
        result = ScrapeResult(
            url=url,
            status="success",
            content=content,
            content_length=len(content),
            layer_used=layer,
            timing_ms=(time.monotonic() - start) * 1000,
        )
        extr = await self.extraction_layer.extract(content, url)
        result.title = extr.title
        result.extracted_text = extr.text
        result.cached = extr.cached
        return result

    async def scrape(self, url: str) -> ScrapeResult:
        """
        Smart scrape: try http first, fallback to browser layers.
        Implements the decision pipeline from the anti-bot spec.
        """
        # Validate URL before any network call
        validate(url)

        start = time.monotonic()
        proxy_rotations = 0

        # Layer 1: HTTP Request (curl_cffi)
        proxy = await self.proxy_manager.get_proxy()
        req_result = await self.request_layer.fetch(url, proxy=proxy)
        if req_result.status == 200 and len(req_result.content) > MIN_CONTENT_LENGTH:
            await self.proxy_manager.report_success(proxy) if proxy else None
            result = await self._build_success_result(
                url, req_result.content, "request", start
            )
            result.proxies_rotated = proxy_rotations
            result.error = req_result.error
            return result

        if proxy:
            await self.proxy_manager.report_failure(proxy)
            proxy_rotations += 1

        # Early exit: terminal network errors skip browser fallback
        if _is_terminal_error(req_result.error):
            timing_ms = (time.monotonic() - start) * 1000
            return ScrapeResult(
                url=url,
                status="error",
                error=req_result.error or "Terminal network error",
                timing_ms=timing_ms,
                proxies_rotated=proxy_rotations,
            )

        # Layer 2: Browser engines (Patchright → Camoufox → nodriver)
        browsers = ["patchright", "camoufox", "nodriver"]
        browser_error: str | None = None
        for engine in browsers:
            browser_result = await self.browser_layer.scrape(url, engine=engine)
            if browser_result.status == 200 and browser_result.html:
                result = await self._build_success_result(
                    url, browser_result.html, f"browser_{engine}", start
                )
                result.proxies_rotated = proxy_rotations
                return result
            browser_error = browser_result.error

        timing_ms = (time.monotonic() - start) * 1000
        # Preserve request layer error — it's more informative than browser errors
        return ScrapeResult(
            url=url,
            status="error",
            error=req_result.error or browser_error or "All layers failed",
            timing_ms=timing_ms,
            proxies_rotated=proxy_rotations,
        )

    async def scrape_with_browser(
        self,
        url: str,
        browser: str = "patchright",
    ) -> ScrapeResult:
        """Force browser mode for JS-heavy pages."""
        validate(url)
        start = time.monotonic()
        browser_result = await self.browser_layer.scrape(url, engine=browser)
        if browser_result.status == 200 and browser_result.html:
            return await self._build_success_result(
                url, browser_result.html, f"browser_{browser}", start
            )
        return ScrapeResult(
            url=url,
            status="error",
            error=browser_result.error or "Browser scraper failed",
            timing_ms=(time.monotonic() - start) * 1000,
        )

    async def check_anonymity(self, url: str) -> dict:
        """Check anonymity by scraping a detection test site."""
        start = time.monotonic()
        result = await self.scrape(url)
        detection_info = {
            "success": result.status == "success",
            "layer_used": result.layer_used,
            "content_length": result.content_length,
            "error": result.error,
            "timing_ms": round((time.monotonic() - start) * 1000, 2),
        }
        # Check for bot detection markers
        if result.content:
            for marker in DETECTION_MARKERS:
                if marker.lower() in result.content.lower():
                    detection_info[f"detected_{marker}"] = True
        return detection_info

    async def scrape_with_captcha(
        self,
        url: str,
        site_key: str,
        service: str = "2captcha",
    ) -> ScrapeResult:
        """Scrape with CAPTCHA solving fallback."""
        result = await self.scrape(url)
        if result.status == "error" or result.status == "blocked":
            logger.info("Attempting CAPTCHA solve for %s", url)
            captcha = await self.captcha_solver.solve_recaptcha_v2(
                site_key=site_key,
                page_url=url,
                service=service,
            )
            if captcha.token:
                result.captcha_solved = True
                # Retry with captcha token — merge query params properly
                parsed = urlparse(url)
                query = parse_qs(parsed.query, keep_blank_values=True)
                query["g-recaptcha-response"] = [captcha.token]
                captcha_url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
                proxy = await self.proxy_manager.get_proxy()
                req_result = await self.request_layer.fetch(
                    captcha_url,
                    proxy=proxy,
                )
                if req_result.status == 200:
                    result.status = "success"
                    result.content = req_result.content
                    result.content_length = len(req_result.content)
        return result
