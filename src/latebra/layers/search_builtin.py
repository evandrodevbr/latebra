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
