"""Pipeline orchestrator for latebra anti-bot evasion.

Implements the 3-layer decision pipeline:
1. Request layer (curl_cffi) - fast, no JS
2. Browser layer (Patchright → Camoufox → nodriver)
3. Extraction layer (Crawl4AI)
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Result from the scraping pipeline."""
    url: str
    status: str  # "success", "blocked", "error"
    content: Optional[str] = None
    content_length: int = 0
    layer_used: str = ""  # "request", "browser_patchright", "browser_camoufox", "browser_nodriver"
    error: Optional[str] = None
    timing_ms: float = 0.0
    captcha_solved: bool = False
    proxies_rotated: int = 0

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
        }


class SmartScrapePipeline:
    """Orchestrates the multi-layer anti-bot evasion pipeline."""

    def __init__(self) -> None:
        self._proxy_rotation_count: int = 0

    async def scrape(self, url: str) -> ScrapeResult:
        """
        Smart scrape: try http first, fallback to browser layers.
        Implements the decision pipeline from the anti-bot spec.
        """
        import time
        start = time.monotonic()

        # Layer 1: HTTP Request (curl_cffi)
        result = await self._try_request_layer(url)
        if result.status == "success":
            result.timing_ms = (time.monotonic() - start) * 1000
            return result

        # Layer 2a: Patchright browser
        result = await self._try_browser_layer(url, engine="patchright")
        if result.status == "success":
            result.timing_ms = (time.monotonic() - start) * 1000
            return result

        # Layer 2b: Camoufox (Firefox stealth)
        result = await self._try_browser_layer(url, engine="camoufox")
        if result.status == "success":
            result.timing_ms = (time.monotonic() - start) * 1000
            return result

        # Layer 2c: nodriver (last resort browser)
        result = await self._try_browser_layer(url, engine="nodriver")
        result.timing_ms = (time.monotonic() - start) * 1000
        return result

    async def scrape_with_browser(
        self,
        url: str,
        browser: str = "patchright",
    ) -> ScrapeResult:
        """Force browser mode for JS-heavy pages."""
        import time
        start = time.monotonic()
        result = await self._try_browser_layer(url, engine=browser)
        result.timing_ms = (time.monotonic() - start) * 1000
        return result

    async def check_anonymity(self, url: str) -> ScrapeResult:
        """Check anonymity by scraping a detection test site."""
        result = await self.scrape(url)
        return result

    async def _try_request_layer(self, url: str) -> ScrapeResult:
        """Layer 1: HTTP request using curl_cffi with TLS impersonation."""
        logger.info("Layer 1: Trying curl_cffi for %s", url)
        result = ScrapeResult(url=url, status="error", layer_used="request")

        try:
            from curl_cffi import requests as cffi_req

            # Random delay for rate limiting (2-8s as per spec)
            await asyncio.sleep(random.uniform(2, 8))

            resp = cffi_req.get(
                url,
                impersonate="chrome120",
                timeout=30,
            )

            if resp.status_code == 200 and len(resp.text) > 500:
                result.status = "success"
                result.content = resp.text
                result.content_length = len(resp.text)
                logger.info("Layer 1: Success with curl_cffi")
            else:
                result.status = "blocked"
                result.error = f"HTTP {resp.status_code}, length={len(resp.text)}"
                result.content = resp.text[:500]
                logger.warning("Layer 1: Blocked - %s", result.error)

        except ImportError:
            result.error = "curl_cffi not installed"
            logger.warning("Layer 1: curl_cffi unavailable")
        except Exception as e:
            result.error = str(e)
            logger.warning("Layer 1: Error - %s", e)

        return result

    async def _try_browser_layer(
        self,
        url: str,
        engine: str = "patchright",
    ) -> ScrapeResult:
        """Layer 2: Browser-based scraping with stealth."""
        layer_name = f"browser_{engine}"
        logger.info("Layer 2: Trying %s for %s", engine, url)
        result = ScrapeResult(url=url, status="error", layer_used=layer_name)

        try:
            if engine == "patchright":
                from patchright.async_api import async_playwright

                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        locale="pt-BR",
                        timezone_id="America/Sao_Paulo",
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                    page = await context.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    content = await page.content()
                    await browser.close()

                    if len(content) > 500:
                        result.status = "success"
                        result.content = content
                        result.content_length = len(content)
                        logger.info("Layer 2: Success with %s", engine)
                    else:
                        result.status = "blocked"
                        result.error = f"Empty/short content ({len(content)} chars)"

            elif engine == "camoufox":
                from camoufox import AsyncNewBrowser

                async with await AsyncNewBrowser(
                    viewport={"width": 1920, "height": 1080},
                    humanize=True,
                    locale="pt-BR",
                ) as browser:
                    page = await browser.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    content = await page.content()

                    if len(content) > 500:
                        result.status = "success"
                        result.content = content
                        result.content_length = len(content)
                        logger.info("Layer 2: Success with Camoufox")
                    else:
                        result.status = "blocked"
                        result.error = f"Empty/short content ({len(content)} chars)"

            elif engine == "nodriver":
                import nodriver as uc

                browser = await uc.start()
                page = await browser.get(url)
                await page.wait_for(5)
                content = await page.content()

                if len(content) > 500:
                    result.status = "success"
                    result.content = content
                    result.content_length = len(content)
                    logger.info("Layer 2: Success with nodriver")
                else:
                    result.status = "blocked"
                    result.error = f"Empty/short content ({len(content)} chars)"

                browser.stop()

        except ImportError as e:
            result.error = f"{engine} not installed: {e}"
            logger.warning("Layer 2: %s unavailable - %s", engine, e)
        except Exception as e:
            result.error = str(e)
            logger.warning("Layer 2: %s error - %s", engine, e)

        return result
