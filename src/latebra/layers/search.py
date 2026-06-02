"""Layer: Web search via SearXNG or built-in engines.

Provides search capabilities for the latebra pipeline.
Uses a self-hosted SearXNG instance for privacy-preserving web search,
with automatic fallback to built-in engines (Google, DuckDuckGo, Bing)
when SearXNG is not available.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from latebra.layers.search_builtin import BuiltInSearchLayer

logger = logging.getLogger(__name__)

DEFAULT_SEARXNG_URL = "http://localhost:8090"


class SearchLayer:
    """Privacy-preserving web search via SearXNG or built-in engines."""

    def __init__(
        self,
        base_url: str = DEFAULT_SEARXNG_URL,
        timeout: int = 10,
        search_backend: str = "auto",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.search_backend = search_backend
        self._builtin = BuiltInSearchLayer(timeout=timeout)
        self._searxng_available: bool | None = None

    async def _detect_searxng(self) -> bool:
        """Check if SearXNG is available."""
        if self._searxng_available is not None:
            return self._searxng_available

        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(
                    f"{self.base_url}/search",
                    params={"q": "test", "format": "json"},
                )
                self._searxng_available = resp.status_code == 200
        except Exception:
            self._searxng_available = False

        return self._searxng_available

    async def search(
        self,
        query: str,
        max_results: int = 10,
        engines: str | None = None,
        categories: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a web search and return structured results.

        Args:
            query: Search terms
            max_results: Maximum number of results to return
            engines: Comma-separated engine list (e.g. "google,duckduckgo")
            categories: Comma-separated category list

        Returns:
            List of dicts with 'title', 'url', 'snippet', 'engine' keys
        """
        # Determine backend
        use_searxng = False

        if self.search_backend == "auto":
            use_searxng = await self._detect_searxng()
            if not use_searxng:
                logger.warning(
                    "SearXNG not available at %s, using built-in engines",
                    self.base_url,
                )
        elif self.search_backend == "searxng":
            use_searxng = True
        # else: use_searxng stays False (built-in)

        if use_searxng:
            return await self._search_searxng(query, max_results, engines, categories)
        else:
            return await self._builtin.search(query, max_results)

    async def _search_searxng(
        self,
        query: str,
        max_results: int,
        engines: str | None,
        categories: str | None,
    ) -> list[dict[str, Any]]:
        """Search using SearXNG."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params: dict[str, str | int] = {
                    "q": query,
                    "format": "json",
                    "pageno": 1,
                }
                if engines:
                    params["engines"] = engines
                if categories:
                    params["categories"] = categories

                resp = await client.get(
                    f"{self.base_url}/search",
                    params=params,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

                results: list[dict[str, Any]] = []
                for item in data.get("results", [])[:max_results]:
                    results.append(
                        {
                            "title": str(item.get("title", "")),
                            "url": str(item.get("url", "")),
                            "snippet": str(
                                item.get("content", "") or item.get("snippet", "")
                            ),
                            "engine": str(
                                item.get("engine", "")
                                or ",".join(item.get("engines", []))
                            ),
                        }
                    )

                logger.info("Search '%s' → %d results", query, len(results))
                return results

        except Exception as e:
            logger.warning("Search failed for '%s': %s", query, e)
            return []
