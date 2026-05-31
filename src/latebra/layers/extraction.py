"""Layer 3: Content extraction with Crawl4AI, CSS/XPath, dedup, and caching."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from latebra.constants import DEFAULT_CACHE_TTL

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    title: str = ""
    text: str = ""
    markdown: str = ""
    html: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    links: list[dict[str, str]] = field(default_factory=list)
    cached: bool = False
    error: str | None = None
    timing_ms: float = 0.0


class ContentCache:
    """SQLite-backed cache with TTL."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.cache/latebra/cache.db")
        dir_path = os.path.dirname(db_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        self.db_path = db_path
        self._local = threading.local()

    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL DEFAULT 3600
                )
            """)
            self._local.conn.commit()
        return self._local.conn

    def _make_key(self, url: str, selector: str | None = None) -> str:
        raw = f"{url}:{selector or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, url: str, selector: str | None = None, ttl: int = DEFAULT_CACHE_TTL) -> dict | None:
        key = self._make_key(url, selector)
        cur = self._conn.execute(
            "SELECT data, created_at, ttl_seconds FROM cache WHERE key = ?",
            (key,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        data_str, created_at, ttl_sec = row
        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(created_at, tz=timezone.utc)).total_seconds()
        if age > ttl_sec:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            return None
        return json.loads(data_str)

    def close(self) -> None:
        """Close thread-local connection if open."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def set(self, url: str, data: dict, selector: str | None = None, ttl: int = DEFAULT_CACHE_TTL) -> None:
        key = self._make_key(url, selector)
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, data, created_at, ttl_seconds) VALUES (?, ?, ?, ?)",
            (key, json.dumps(data), datetime.now(timezone.utc).timestamp(), ttl),
        )
        self._conn.commit()


class AsyncExtractionLayer:
    """Content extraction with Crawl4AI, CSS selectors, and caching."""

    def __init__(self, cache_ttl: int = DEFAULT_CACHE_TTL, use_cache: bool = True):
        self.cache_ttl = cache_ttl
        self.use_cache = use_cache
        self.cache = ContentCache() if use_cache else None

    async def extract(
        self,
        html: str,
        url: str,
        selector: str | None = None,
    ) -> ExtractionResult:
        result = ExtractionResult()
        start = asyncio.get_event_loop().time()

        # Check cache
        if self.cache:
            cached = self.cache.get(url, selector, ttl=self.cache_ttl)
            if cached:
                result = ExtractionResult(**cached)
                result.cached = True
                result.timing_ms = 0
                return result

        try:
            await self._extract_crawl4ai(html, url, result, selector)
        except ImportError:
            self._extract_fallback(html, url, result, selector)
        except Exception as e:
            logger.warning("Crawl4AI extraction failed: %s", e)
            self._extract_fallback(html, url, result, selector)

        result.timing_ms = (asyncio.get_event_loop().time() - start) * 1000

        # Store in cache
        if self.cache and not result.error:
            self.cache.set(url, {
                "title": result.title,
                "text": result.text,
                "markdown": result.markdown,
                "html": result.html,
                "metadata": result.metadata,
                "links": result.links,
                "error": None,
                "timing_ms": result.timing_ms,
                "cached": False,
            }, selector, ttl=self.cache_ttl)

        return result

    async def _extract_crawl4ai(
        self, html: str, url: str, result: ExtractionResult, selector: str | None = None
    ) -> None:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            crawl_result = await crawler.arun(
                url=url,
                raw_html=html,
                bypass_cache=True,
                word_count_threshold=10,
                extraction_strategy="no_extraction",
            )
            result.title = getattr(crawl_result, "title", "") or ""
            result.text = getattr(crawl_result, "extracted_content", "") or ""
            result.markdown = getattr(crawl_result, "markdown", "") or ""
            result.metadata = {}

    def _extract_fallback(
        self, html: str, url: str, result: ExtractionResult, selector: str | None = None
    ) -> None:
        """Simple fallback extraction without Crawl4AI."""
        from html.parser import HTMLParser

        class TitleParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_title = False
                self.title = ""

            def handle_starttag(self, tag, attrs):
                if tag == "title":
                    self.in_title = True

            def handle_endtag(self, tag):
                if tag == "title":
                    self.in_title = False

            def handle_data(self, data):
                if self.in_title:
                    self.title += data

        parser = TitleParser()
        parser.feed(html)
        result.title = parser.title or ""
        result.html = html
        result.text = html

        # Simple link extraction
        import re
        links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
        seen = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                result.links.append({"url": link, "text": ""})
