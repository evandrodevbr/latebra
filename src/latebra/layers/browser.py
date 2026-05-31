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

    def __init__(self, stealth: bool = True):
        self.stealth = stealth

    def _random_viewport(self) -> tuple[int, int]:
        return random.choice(self.VIEWPORTS)

    def _random_locale(self) -> str:
        return random.choice(self.LOCALES)

    def _random_timezone(self) -> str:
        return random.choice(self.TIMEZONES)

    def _random_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    async def scrape(self, url: str, engine: str = "patchright") -> BrowserResult:
        """Scrape URL with browser, falling back through engine chain on failure."""
        result = BrowserResult()
        result.url = url
        start = asyncio.get_event_loop().time()

        engines_to_try = self.ENGINES[self.ENGINES.index(engine):] if engine in self.ENGINES else self.ENGINES

        for eng in engines_to_try:
            try:
                result.engine = eng
                if eng == "patchright":
                    await self._scrape_patchright(url, result)
                elif eng == "camoufox":
                    await self._scrape_camoufox(url, result)
                elif eng == "nodriver":
                    await self._scrape_nodriver(url, result)

                if result.html:
                    result.status = 200
                    break

            except Exception as e:
                logger.warning("Browser engine %s failed: %s", eng, e)
                result.error = str(e)
                continue

        result.timing_ms = (asyncio.get_event_loop().time() - start) * 1000
        return result

    async def _scrape_patchright(self, url: str, result: BrowserResult) -> None:
        try:
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
                    await page.add_init_script("""
                        Object.defineProperty(navigator, "webdriver", { get: () => undefined });
                        Object.defineProperty(navigator, "plugins", { get: () => [1,2,3] });
                        window.chrome = { runtime: {} };
                    """)

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(random.randint(1000, 3000))
                result.html = await page.content()
                await browser.close()
        except ImportError:
            raise

    async def _scrape_camoufox(self, url: str, result: BrowserResult) -> None:
        try:
            from camoufox import Camoufox
            async with Camoufox(headless=True) as browser:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(1000, 2000))
                result.html = await page.content()
        except ImportError:
            raise

    async def _scrape_nodriver(self, url: str, result: BrowserResult) -> None:
        try:
            import nodriver as nd
            browser = await nd.start()
            page = await browser.get(url)
            await page.wait_for(nd.By.TAG_NAME, "body", timeout=15)
            await asyncio.sleep(random.uniform(1, 2))
            result.html = await page.content()
            browser.stop()
        except ImportError:
            raise
