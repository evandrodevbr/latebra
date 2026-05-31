"""Layer: Deep crawler for site discovery and mapping.

Follows links from a seed URL up to a configured depth and page limit.
Uses the request layer for fetching and regex for link extraction.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from latebra.layers.request import AsyncRequestLayer

logger = logging.getLogger(__name__)

# Extract <a href="..."> links from HTML — matches both absolute and relative URLs
_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"#][^"\']*)["\']', re.IGNORECASE)


@dataclass
class CrawlPage:
    url: str = ""
    title: str = ""
    links: list[str] = field(default_factory=list)
    status: int = 0
    error: str | None = None


class CrawlerLayer:
    """Site crawler with depth and page limits."""

    def __init__(
        self,
        max_depth: int = 2,
        max_pages: int = 50,
        same_domain: bool = True,
        timeout: int = 15,
    ) -> None:
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.same_domain = same_domain
        self.timeout = timeout
        self.request = AsyncRequestLayer(timeout=timeout)

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract absolute HTTP(S) links from HTML."""
        links: list[str] = []
        for match in _LINK_RE.finditer(html):
            href = match.group(1)
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https"):
                links.append(absolute)
        return links

    def _extract_title(self, html: str) -> str:
        """Extract <title> from HTML."""
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _same_domain_filter(self, links: list[str], seed_domain: str) -> list[str]:
        """Filter links to same domain as seed."""
        return [l for l in links if urlparse(l).netloc == seed_domain]

    async def crawl(self, seed_url: str) -> list[dict[str, Any]]:
        """Crawl starting from seed_url up to max_depth and max_pages.

        Returns list of dicts with 'url', 'title', 'links', 'status', 'error'.
        """
        pages: list[dict[str, Any]] = []
        visited: set[str] = set()
        seed_domain = urlparse(seed_url).netloc

        # BFS queue: (url, depth)
        queue: list[tuple[str, int]] = [(seed_url, 0)]

        while queue and len(pages) < self.max_pages:
            url, depth = queue.pop(0)

            if url in visited:
                continue
            visited.add(url)

            # Fetch page
            result = await self.request.fetch(url)
            page: dict[str, Any] = {
                "url": url,
                "title": "",
                "links": [],
                "status": result.status,
                "error": result.error,
                "depth": depth,
            }

            if result.status == 200 and result.content:
                page["title"] = self._extract_title(result.content)
                links = self._extract_links(result.content, url)
                if self.same_domain:
                    links = self._same_domain_filter(links, seed_domain)
                page["links"] = links[:100]  # cap per page

                # Enqueue links for next depth level
                if depth < self.max_depth:
                    for link in links:
                        if link not in visited:
                            queue.append((link, depth + 1))

            pages.append(page)
            logger.debug(
                "Crawled %s (depth=%d, %d links, %d pages total)",
                url, depth, len(page["links"]), len(pages),
            )

        logger.info(
            "Crawl complete: %d pages from %s (depth=%d)",
            len(pages), seed_url, self.max_depth,
        )
        return pages
