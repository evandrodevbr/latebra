"""Layer 1: HTTP request layer with TLS impersonation and proxy support."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    status: int = 0
    content: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    timing_ms: float = 0.0
    proxy_used: str | None = None


class AsyncRequestLayer:
    """Layer 1 HTTP requests with TLS fingerprint impersonation."""

    IMPERSONATE_OPTIONS = [
        "chrome120", "chrome123", "chrome124",
        "safari15_5", "safari17_0",
        "edge120", "firefox120",
    ]

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 2,
        impersonate: str = "chrome120",
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.impersonate = impersonate
        self._session = None

    async def _ensure_session(self):
        if self._session is None:
            try:
                from curl_cffi.requests import AsyncSession
                self._session = AsyncSession(
                    impersonate=self.impersonate,
                    timeout=self.timeout,
                )
                logger.info("curl_cffi session created (impersonate=%s)", self.impersonate)
            except ImportError:
                logger.warning("curl_cffi not available, falling back to httpx")
                import httpx
                self._session = httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    follow_redirects=True,
                )
                self._impersonation_mode = "httpx"

    async def fetch(self, url: str, proxy: str | None = None) -> RequestResult:
        result = RequestResult()
        await self._ensure_session()
        start = asyncio.get_event_loop().time()

        for attempt in range(self.max_retries + 1):
            try:
                kwargs = {}
                if proxy:
                    kwargs["proxy"] = proxy
                    result.proxy_used = proxy

                resp = await self._session.get(url, **kwargs)
                result.status = resp.status_code
                result.content = resp.text
                result.headers = dict(resp.headers)
                break

            except Exception as e:
                logger.warning("Request attempt %d failed: %s", attempt + 1, e)
                result.error = str(e)
                if attempt < self.max_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))

        result.timing_ms = (asyncio.get_event_loop().time() - start) * 1000
        return result

    async def close(self):
        if self._session:
            await self._session.aclose() if hasattr(self._session, "aclose") else None
