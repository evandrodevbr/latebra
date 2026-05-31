"""Layer 2: Browser automation with stealth profile and multi-engine fallback."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any

from latebra.constants import (
    ENGINES,
    LOCALES,
    TIMEZONES,
    USER_AGENTS,
    VIEWPORTS,
)

logger = logging.getLogger(__name__)


@dataclass
class BrowserResult:
    html: str = ""
    url: str = ""
    status: int = 0
    engine: str = ""
    error: str | None = None
    timing_ms: float = 0.0
    screenshot: str | None = None


class AsyncBrowserLayer:
    """Browser scraping with stealth profiles and engine fallback chain."""

    ENGINES = ENGINES
    VIEWPORTS = VIEWPORTS
    LOCALES = LOCALES
    TIMEZONES = TIMEZONES

    _STEALTH_SCRIPT = (
        'Object.defineProperty(navigator, "webdriver", { get: () => undefined });'
        'Object.defineProperty(navigator, "plugins", { get: () => [1,2,3] });'
        'window.chrome = { runtime: {} };'
    )

    def __init__(self, stealth: bool = True):
        self.stealth = stealth
        self._warm_browser = None
        self._warm_context = None
        self._warm_engine: str | None = None

    def _random_viewport(self) -> tuple[int, int]:
        return random.choice(self.VIEWPORTS)

    def _random_locale(self) -> str:
        return random.choice(self.LOCALES)

    def _random_timezone(self) -> str:
        return random.choice(self.TIMEZONES)

    def _random_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    async def scrape(self, url: str, engine: str = "patchright") -> BrowserResult:
        """Scrape URL with the specified browser engine only.

        No internal fallback — pipeline manages fallback across engines.
        """
        result = BrowserResult()
        result.url = url
        start = asyncio.get_event_loop().time()

        if engine not in self.ENGINES:
            result.error = f"Unknown engine: {engine}"
            result.timing_ms = (asyncio.get_event_loop().time() - start) * 1000
            return result

        try:
            result.engine = engine
            if engine == "patchright":
                await self._scrape_patchright(url, result)
            elif engine == "camoufox":
                await self._scrape_camoufox(url, result)
            elif engine == "nodriver":
                await self._scrape_nodriver(url, result)

            if result.html:
                result.status = 200

        except Exception as e:
            logger.warning("Browser engine %s failed: %s", engine, e)
            result.error = str(e)

        result.timing_ms = (asyncio.get_event_loop().time() - start) * 1000
        return result

    async def warm_up(self, engine: str = "patchright") -> None:
        """Pre-launch a browser instance for faster subsequent scrapes.

        Keeps the browser + context alive between calls.  Call warm_down()
        when done to release resources.
        """
        if engine == "patchright":
            from patchright.async_api import async_playwright
            self._warm_playwright = await async_playwright().__aenter__()
            self._warm_browser = await self._warm_playwright.chromium.launch(
                headless=True
            )
            viewport = self._random_viewport()
            self._warm_context = await self._warm_browser.new_context(
                viewport={"width": viewport[0], "height": viewport[1]},
                locale=self._random_locale(),
                timezone_id=self._random_timezone(),
                user_agent=self._random_user_agent(),
            )
            self._warm_engine = engine
            logger.info("Browser warm pool ready (engine=%s)", engine)
        else:
            logger.warning("warm_up only supports patchright, got %s", engine)

    async def warm_down(self) -> None:
        """Close the warm browser pool and release resources."""
        if self._warm_context:
            await self._warm_context.close()
            self._warm_context = None
        if self._warm_browser:
            await self._warm_browser.close()
            self._warm_browser = None
        if hasattr(self, "_warm_playwright") and self._warm_playwright:
            await self._warm_playwright.__aexit__(None, None, None)
            self._warm_playwright = None
        self._warm_engine = None
        logger.info("Browser warm pool shut down")

    async def _scrape_patchright(self, url: str, result: BrowserResult) -> None:
        try:
            # Use warm pool if available — reuses browser + context
            if self._warm_browser and self._warm_context and self._warm_engine == "patchright":
                page = await self._warm_context.new_page()
                if self.stealth:
                    await page.add_init_script(self._STEALTH_SCRIPT)
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(random.randint(1000, 3000))
                result.html = await page.content()
                await page.close()
                return

            # Cold launch
            from patchright.async_api import async_playwright
            async with async_playwright() as p:
                viewport = self._random_viewport()
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": viewport[0], "height": viewport[1]},
                    locale=self._random_locale(),
                    timezone_id=self._random_timezone(),
                    user_agent=self._random_user_agent(),
                )
                page = await context.new_page()

                if self.stealth:
                    await page.add_init_script(self._STEALTH_SCRIPT)

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(random.randint(1000, 3000))
                result.html = await page.content()
                await browser.close()
        except ImportError:
            raise

    async def _scrape_camoufox(self, url: str, result: BrowserResult) -> None:
        try:
            from camoufox import AsyncCamoufox
            async with AsyncCamoufox(headless=True) as browser:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(1000, 2000))
                result.html = await page.content()
        except ImportError:
            raise

    async def _scrape_nodriver(self, url: str, result: BrowserResult) -> None:
        try:
            import nodriver as nd
            browser = await nd.start(headless=True)
            page = await browser.get(url)
            await page.wait_for("body", timeout=15)
            await browser.sleep(random.uniform(1, 2))
            result.html = await page.get_content()
            browser.stop()
        except ImportError:
            raise
