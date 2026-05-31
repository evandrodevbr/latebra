"""Layer: Web search via SearXNG.

Provides search capabilities for the latebra pipeline.
Uses a self-hosted SearXNG instance for privacy-preserving web search.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SEARXNG_URL = "http://localhost:8090"


@dataclass
class SearchResult:
    title: str = ""
    url: str = ""
    snippet: str = ""
    engine: str = ""


class SearchLayer:
    """Privacy-preserving web search via SearXNG."""

    def __init__(
        self,
        base_url: str = DEFAULT_SEARXNG_URL,
        timeout: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

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
                    results.append({
                        "title": str(item.get("title", "")),
                        "url": str(item.get("url", "")),
                        "snippet": str(item.get("content", "") or item.get("snippet", "")),
                        "engine": str(item.get("engine", "") or ",".join(item.get("engines", []))),
                    })

                logger.info("Search '%s' → %d results", query, len(results))
                return results

        except Exception as e:
            logger.warning("Search failed for '%s': %s", query, e)
            return []
