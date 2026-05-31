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

from latebra.captcha.solver import CaptchaSolver
from latebra.layers.browser import AsyncBrowserLayer
from latebra.layers.extraction import AsyncExtractionLayer
from latebra.layers.request import AsyncRequestLayer
from latebra.proxy.manager import ProxyManager

logger = logging.getLogger(__name__)


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
        self._proxy_rotation_count: int = 0

    async def scrape(self, url: str) -> ScrapeResult:
        """
        Smart scrape: try http first, fallback to browser layers.
        Implements the decision pipeline from the anti-bot spec.
        """
        start = time.monotonic()

        # Layer 1: HTTP Request (curl_cffi)
        proxy = await self.proxy_manager.get_proxy()
        req_result = await self.request_layer.fetch(url, proxy=proxy)
        if req_result.status == 200 and len(req_result.content) > 500:
            await self.proxy_manager.report_success(proxy) if proxy else None
            result = ScrapeResult(
                url=url,
                status="success",
                content=req_result.content,
                content_length=len(req_result.content),
                layer_used="request",
                timing_ms=(time.monotonic() - start) * 1000,
                error=req_result.error,
                proxies_rotated=self._proxy_rotation_count,
            )
            # Layer 3: extraction
            extr = await self.extraction_layer.extract(req_result.content, url)
            result.title = extr.title
            result.extracted_text = extr.text
            return result

        if proxy:
            await self.proxy_manager.report_failure(proxy)
            self._proxy_rotation_count += 1

        # Layer 2a: Patchright browser
        browser_result = await self.browser_layer.scrape(url, engine="patchright")
        if browser_result.status == 200 and browser_result.html:
            result = ScrapeResult(
                url=url,
                status="success",
                content=browser_result.html,
                content_length=len(browser_result.html),
                layer_used=f"browser_{browser_result.engine}",
                timing_ms=(time.monotonic() - start) * 1000,
                proxies_rotated=self._proxy_rotation_count,
            )
            extr = await self.extraction_layer.extract(browser_result.html, url)
            result.title = extr.title
            result.extracted_text = extr.text
            return result

        # Layer 2b: Camoufox
        browser_result = await self.browser_layer.scrape(url, engine="camoufox")
        if browser_result.status == 200 and browser_result.html:
            result = ScrapeResult(
                url=url,
                status="success",
                content=browser_result.html,
                content_length=len(browser_result.html),
                layer_used=f"browser_{browser_result.engine}",
                timing_ms=(time.monotonic() - start) * 1000,
                proxies_rotated=self._proxy_rotation_count,
            )
            extr = await self.extraction_layer.extract(browser_result.html, url)
            result.title = extr.title
            result.extracted_text = extr.text
            return result

        # Layer 2c: nodriver (last resort)
        browser_result = await self.browser_layer.scrape(url, engine="nodriver")
        timing_ms = (time.monotonic() - start) * 1000
        if browser_result.status == 200 and browser_result.html:
            result = ScrapeResult(
                url=url,
                status="success",
                content=browser_result.html,
                content_length=len(browser_result.html),
                layer_used=f"browser_{browser_result.engine}",
                timing_ms=timing_ms,
                proxies_rotated=self._proxy_rotation_count,
            )
            extr = await self.extraction_layer.extract(browser_result.html, url)
            result.title = extr.title
            result.extracted_text = extr.text
            return result

        return ScrapeResult(
            url=url,
            status="error",
            error=browser_result.error or req_result.error or "All layers failed",
            timing_ms=timing_ms,
            proxies_rotated=self._proxy_rotation_count,
        )

    async def scrape_with_browser(
        self,
        url: str,
        browser: str = "patchright",
    ) -> ScrapeResult:
        """Force browser mode for JS-heavy pages."""
        start = time.monotonic()
        browser_result = await self.browser_layer.scrape(url, engine=browser)
        timing = (time.monotonic() - start) * 1000
        if browser_result.status == 200 and browser_result.html:
            result = ScrapeResult(
                url=url,
                status="success",
                content=browser_result.html,
                content_length=len(browser_result.html),
                layer_used=f"browser_{browser}",
                timing_ms=timing,
            )
            extr = await self.extraction_layer.extract(browser_result.html, url)
            result.title = extr.title
            result.extracted_text = extr.text
            result.cached = extr.cached
            return result
        return ScrapeResult(
            url=url,
            status="error",
            error=browser_result.error or "Browser scraper failed",
            timing_ms=timing,
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
            "proxies_rotated": self._proxy_rotation_count,
        }
        # Check for bot detection markers
        if result.content:
            markers = [
                "automated",
                "bot",
                "captcha",
                "cloudflare",
                "blocked",
                "denied",
                "unusual traffic",
            ]
            for marker in markers:
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
                # Retry with captcha token
                proxy = await self.proxy_manager.get_proxy()
                req_result = await self.request_layer.fetch(
                    f"{url}?g-recaptcha-response={captcha.token}",
                    proxy=proxy,
                )
                if req_result.status == 200:
                    result.status = "success"
                    result.content = req_result.content
                    result.content_length = len(req_result.content)
        return result
