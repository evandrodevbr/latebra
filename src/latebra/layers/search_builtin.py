"""Built-in search engines for latebra.

Provides search capabilities without SearXNG dependency.
Engines: Google, DuckDuckGo, Bing.

Autor: Evandro Fonseca Junior
Licença: MIT
"""

from __future__ import annotations

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseSearchEngine(ABC):
    """Abstract base class for search engines."""

    @abstractmethod
    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Execute search and return results."""
        ...


class DuckDuckGoEngine(BaseSearchEngine):
    """DuckDuckGo search via ddgs library."""

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search DuckDuckGo and return results."""
        try:
            from ddgs import DDGS

            results = DDGS().text(query, max_results=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "engine": "duckduckgo",
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            return []


class GoogleEngine(BaseSearchEngine):
    """Google search via ddgs library."""

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search Google and return results."""
        try:
            from ddgs import DDGS

            results = DDGS().text(query, max_results=max_results, backend="google")
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "engine": "google",
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Google search failed: %s", e)
            return []


class BingEngine(BaseSearchEngine):
    """Bing search via ddgs library."""

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search Bing and return results."""
        try:
            from ddgs import DDGS

            results = DDGS().text(query, max_results=max_results, backend="bing")
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "engine": "bing",
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Bing search failed: %s", e)
            return []


class BuiltInSearchLayer:
    """Search across multiple built-in engines with round-robin merge."""

    def __init__(self, timeout: int = 10, max_concurrent: int = 3) -> None:
        self._engines = [
            DuckDuckGoEngine(timeout=timeout),
            GoogleEngine(timeout=timeout),
            BingEngine(timeout=timeout),
        ]
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search all engines concurrently and merge results."""

        async def _search_engine(
            engine: BaseSearchEngine,
        ) -> list[dict[str, Any]]:
            async with self._semaphore:
                return await engine.search(query, max_results=max_results)

        # Run all engines concurrently
        tasks = [_search_engine(engine) for engine in self._engines]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in all_results if isinstance(r, list)]

        # Round-robin merge
        merged = []
        seen_urls: set[str] = set()
        max_len = max((len(r) for r in valid_results), default=0)

        for i in range(max_len):
            for engine_results in valid_results:
                if i < len(engine_results):
                    result = engine_results[i]
                    url = result.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        merged.append(result)
                        if len(merged) >= max_results:
                            return merged

        return merged
