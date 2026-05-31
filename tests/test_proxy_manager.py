"""Tests for the proxy rotation manager."""

from __future__ import annotations

import time

import pytest

from latebra.proxy.manager import ProxyEntry, ProxyManager


class TestProxyEntry:
    """Test the ProxyEntry dataclass."""

    def test_default_healthy(self):
        entry = ProxyEntry(url="http://proxy:8080")
        assert entry.is_healthy is True
        assert entry.is_banned is False

    def test_three_failures_bans(self):
        entry = ProxyEntry(url="http://proxy:8080")
        entry.record_failure()
        entry.record_failure()
        assert entry.is_healthy is True
        entry.record_failure()
        assert entry.is_healthy is False
        assert entry.is_banned is True

    def test_success_resets_failures(self):
        entry = ProxyEntry(url="http://proxy:8080")
        entry.record_failure()
        entry.record_failure()
        entry.record_success()
        assert entry.failed_count == 0
        assert entry.banned_until is None
        assert entry.is_healthy is True


class TestProxyManager:
    """Test the ProxyManager."""

    def test_init_empty(self):
        pm = ProxyManager()
        assert pm.stats["total_proxies"] == 0

    def test_init_with_proxies(self, proxies):
        pm = ProxyManager(proxies=proxies)
        assert pm.stats["total_proxies"] == 2

    def test_add_proxy(self):
        pm = ProxyManager()
        pm.add_proxy("http://proxy1:8080")
        assert pm.stats["total_proxies"] == 1

    def test_remove_proxy(self):
        pm = ProxyManager(proxies=["http://proxy1:8080"])
        assert pm.remove_proxy("http://proxy1:8080") is True
        assert pm.stats["total_proxies"] == 0

    def test_remove_nonexistent(self):
        pm = ProxyManager()
        assert pm.remove_proxy("http://nonexistent") is False

    def test_get_proxy_empty(self):
        import asyncio
        pm = ProxyManager()
        result = asyncio.run(pm.get_proxy())
        assert result is None

    def test_get_proxy(self):
        import asyncio
        pm = ProxyManager(proxies=["http://proxy1:8080", "http://proxy2:8080"])
        proxy = asyncio.run(pm.get_proxy())
        assert proxy in ["http://proxy1:8080", "http://proxy2:8080"]

    def test_round_robin_rotation(self):
        import asyncio
        pm = ProxyManager(proxies=["http://p1", "http://p2"], rotation="round_robin")
        p1 = asyncio.run(pm.get_proxy())
        p2 = asyncio.run(pm.get_proxy())
        p3 = asyncio.run(pm.get_proxy())
        # Round robin: p1, p2, p1, ...
        assert p1 == "http://p1"
        assert p2 == "http://p2"
        assert p3 == "http://p1"  # wraps around

    def test_random_rotation(self):
        import asyncio
        pm = ProxyManager(
            proxies=["http://p1", "http://p2", "http://p3"],
            rotation="random",
        )
        results = set()
        for _ in range(10):
            results.add(asyncio.run(pm.get_proxy()))
        assert len(results) <= 3

    def test_report_failure(self):
        import asyncio
        pm = ProxyManager(proxies=["http://proxy1:8080"])
        asyncio.run(pm.report_failure("http://proxy1:8080"))
        assert pm._entries[0].failed_count == 1

    def test_report_success(self):
        import asyncio
        pm = ProxyManager(proxies=["http://proxy1:8080"])
        asyncio.run(pm.report_failure("http://proxy1:8080"))
        asyncio.run(pm.report_success("http://proxy1:8080"))
        assert pm._entries[0].failed_count == 0

    def test_health_check(self):
        import asyncio
        pm = ProxyManager(proxies=["http://p1", "http://p2"])
        stats = asyncio.run(pm.health_check())
        assert stats["healthy"] == 2
        assert stats["total"] == 2
