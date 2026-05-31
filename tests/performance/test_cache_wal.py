"""Test SQLite WAL mode optimization for extraction cache."""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from latebra.layers.extraction import ContentCache


def test_cache_uses_wal_mode():
    """ContentCache should use WAL journal mode for better concurrent reads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cache = ContentCache(str(db_path))

        # Trigger connection creation
        _ = cache._conn

        row = cache._conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0].upper() == "WAL", (
            f"Cache should use WAL mode for performance, got {row[0]}"
        )

        cache.close()


def test_cache_has_performance_pragmas():
    """Cache should set performance PRAGMAs at init."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cache = ContentCache(str(db_path))
        _ = cache._conn  # trigger init

        # Check synchronous mode (should be NORMAL, not FULL)
        row = cache._conn.execute("PRAGMA synchronous").fetchone()
        assert row[0] in (1, "1"), (
            f"synchronous should be NORMAL (1), got {row[0]}"
        )

        cache.close()


def test_cache_operations_work_with_wal():
    """Set/get/ttl-expire should work correctly with WAL mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cache = ContentCache(str(db_path))

        # Write
        cache.set("http://example.com", {"title": "Test"})
        # Read
        data = cache.get("http://example.com")
        assert data is not None
        assert data["title"] == "Test"

        # TTL expire (negative TTL = already expired)
        cache.set("http://example.com/expired", {"title": "Old"}, ttl=-1)
        data = cache.get("http://example.com/expired", ttl=-1)
        assert data is None, "Expired cache should return None"

        cache.close()
