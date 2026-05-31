"""Layer: Browser interaction — click, type, navigate.

Provides interactive browser capabilities on top of the existing AsyncBrowserLayer.
Enables agents to interact with JavaScript-heavy SPAs, fill forms, and click buttons.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class InteractLayer:
    """Browser interaction layer for clicking, typing, and navigating.

    Wraps AsyncBrowserLayer with high-level interaction primitives.
    """

    def __init__(
        self,
        browser: Any | None = None,
        timeout: int = 30,
    ) -> None:
        from latebra.layers.browser import AsyncBrowserLayer

        self._browser = browser or AsyncBrowserLayer(stealth=True)
        self._timeout = timeout
        self._page: Any = None
        self._current_url: str = ""

    async def navigate(self, url: str) -> dict[str, Any]:
        """Navigate to a URL and return page info."""
        from patchright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            self._page = await context.new_page()

            await self._page.goto(url, wait_until="domcontentloaded", timeout=self._timeout * 1000)
            self._current_url = url

            title = await self._page.title()
            html = await self._page.content()

            return {
                "url": url,
                "title": title,
                "status": 200,
                "html_length": len(html),
            }

    async def click(self, selector: str) -> dict[str, Any]:
        """Click an element by CSS selector."""
        if not self._page:
            return {"error": "No page loaded — call navigate() first"}

        try:
            await self._page.click(selector, timeout=self._timeout * 1000)
            await self._page.wait_for_timeout(1000)  # let page react

            new_url = self._page.url if hasattr(self._page, "url") else self._current_url
            return {
                "selector": selector,
                "clicked": True,
                "new_url": new_url,
                "error": None,
            }
        except Exception as e:
            return {
                "selector": selector,
                "clicked": False,
                "error": str(e),
            }

    async def type_text(self, selector: str, text: str) -> dict[str, Any]:
        """Type text into an input element."""
        if not self._page:
            return {"error": "No page loaded — call navigate() first"}

        try:
            await self._page.fill(selector, text, timeout=self._timeout * 1000)
            return {
                "selector": selector,
                "typed": True,
                "text": text,
                "error": None,
            }
        except Exception as e:
            return {
                "selector": selector,
                "typed": False,
                "error": str(e),
            }

    async def get_content(self) -> str:
        """Get current page HTML content."""
        if not self._page:
            return ""
        return await self._page.content()

    async def screenshot(self) -> str | None:
        """Take a screenshot and return base64-encoded PNG."""
        if not self._page:
            return None
        import base64
        screenshot_bytes = await self._page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode()
