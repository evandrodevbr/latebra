"""Proxy rotation manager with circuit breaker pattern."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProxyEntry:
    url: str
    failed_count: int = 0
    last_failure: datetime | None = None
    banned_until: datetime | None = None
    total_uses: int = 0
    total_success: int = 0
    total_timeout: int = 0

    @property
    def is_banned(self) -> bool:
        if self.banned_until is None:
            return False
        return datetime.now(timezone.utc) < self.banned_until

    @property
    def is_healthy(self) -> bool:
        return self.failed_count < 3 and not self.is_banned

    def record_failure(self):
        self.failed_count += 1
        self.last_failure = datetime.now(timezone.utc)
        if self.failed_count >= 3:
            cooldown = min(30 * (2 ** (self.failed_count - 3)), 3600)
            self.banned_until = datetime.now(timezone.utc) + timedelta(seconds=cooldown)
            logger.info("Proxy %s banned for %ds", self.url, cooldown)

    def record_success(self):
        self.total_success += 1
        self.failed_count = 0
        self.banned_until = None

    def record_use(self):
        self.total_uses += 1

    def record_timeout(self):
        self.total_timeout += 1


class ProxyManager:
    """Manages proxy rotation, health checks, and circuit breaking."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        rotation: str = "round_robin",
        health_check_url: str = "https://httpbin.org/ip",
    ):
        self._entries: list[ProxyEntry] = []
        self._index = 0
        self.rotation = rotation
        self.health_check_url = health_check_url
        self._lock = asyncio.Lock()
        self._health_task: asyncio.Task | None = None

        if proxies:
            for p in proxies:
                self._entries.append(ProxyEntry(url=p))

    def add_proxy(self, url: str) -> None:
        self._entries.append(ProxyEntry(url=url))
        logger.info("Added proxy: %s", url)

    def remove_proxy(self, url: str) -> bool:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.url != url]
        return len(self._entries) < before

    async def get_proxy(self) -> str | None:
        """Get next healthy proxy based on rotation strategy."""
        if not self._entries:
            return None

        async with self._lock:
            healthy = [e for e in self._entries if e.is_healthy]
            if not healthy:
                logger.warning("No healthy proxies available")
                # Try banned proxies as last resort
                healthy = sorted(self._entries, key=lambda e: e.banned_until or datetime.min)
                if healthy:
                    return healthy[0].url
                return None

            if self.rotation == "round_robin":
                entry = healthy[self._index % len(healthy)]
                self._index += 1
            elif self.rotation == "random":
                entry = random.choice(healthy)
            else:  # least_used
                entry = min(healthy, key=lambda e: e.total_uses)

            entry.record_use()
            return entry.url

    async def report_failure(self, proxy_url: str) -> None:
        async with self._lock:
            for entry in self._entries:
                if entry.url == proxy_url:
                    entry.record_failure()
                    break

    async def report_success(self, proxy_url: str) -> None:
        async with self._lock:
            for entry in self._entries:
                if entry.url == proxy_url:
                    entry.record_success()
                    break

    async def health_check(self) -> dict[str, Any]:
        """Check all proxies and return status report."""
        results = {"healthy": 0, "banned": 0, "total": len(self._entries)}
        for entry in self._entries:
            if entry.is_healthy:
                results["healthy"] += 1
            else:
                results["banned"] += 1
        return results

    async def health_check_all(self) -> list[dict]:
        """Validate all proxies concurrently and return per-proxy results.

        Returns list of dicts with 'url', 'healthy', 'error' keys.
        Proxies that fail validation are marked via report_failure.
        """
        async def _check_one(entry: ProxyEntry) -> dict:
            try:
                from latebra.layers.request import AsyncRequestLayer
                layer = AsyncRequestLayer(timeout=5, max_retries=0)
                result = await layer.fetch(self.health_check_url, proxy=entry.url)
                if result.status == 200:
                    await self.report_success(entry.url)
                    return {"url": entry.url, "healthy": True, "error": None}
                else:
                    await self.report_failure(entry.url)
                    return {"url": entry.url, "healthy": False, "error": f"HTTP {result.status}"}
            except Exception as e:
                await self.report_failure(entry.url)
                return {"url": entry.url, "healthy": False, "error": str(e)}

        if not self._entries:
            return []
        tasks = [_check_one(e) for e in self._entries]
        return await asyncio.gather(*tasks)

    async def start_background_health_checks(self, interval: int = 300) -> None:
        """Start periodic health checks in background."""

        async def _check_loop():
            while True:
                await asyncio.sleep(interval)
                await self.health_check()

        self._health_task = asyncio.create_task(_check_loop())

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_proxies": len(self._entries),
            "healthy": sum(1 for e in self._entries if e.is_healthy),
            "banned": sum(1 for e in self._entries if not e.is_healthy),
            "rotation": self.rotation,
        }
