"""Tests for latebra.config module — centralized configuration."""

from __future__ import annotations

import os

from latebra.config import LatebraConfig, _parse_proxies


class TestParseProxies:
    """Test proxy string parsing."""

    def test_empty_string(self):
        assert _parse_proxies("") == []

    def test_single_proxy(self):
        result = _parse_proxies("socks5://user:pass@host:1080")
        assert result == ["socks5://user:pass@host:1080"]

    def test_multiple_proxies(self):
        result = _parse_proxies("socks5://a:1,http://b:2")
        assert len(result) == 2
        assert "socks5://a:1" in result
        assert "http://b:2" in result

    def test_whitespace_handling(self):
        result = _parse_proxies("  socks5://a:1  ,  http://b:2  ")
        assert result == ["socks5://a:1", "http://b:2"]

    def test_invalid_skipped(self):
        result = _parse_proxies("invalid,http://valid:8080")
        assert result == ["http://valid:8080"]

    def test_empty_entries_skipped(self):
        result = _parse_proxies("http://a,,")
        assert result == ["http://a"]


class TestLatebraConfig:
    """Test LatebraConfig dataclass and from_env."""

    def test_default_values(self):
        config = LatebraConfig()
        assert config.proxies == []
        assert config.two_captcha_key is None
        assert config.capsolver_key is None
        assert config.stealth_enabled is True
        assert config.request_timeout == 30.0
        assert config.max_retries == 2
        assert config.log_level == "INFO"
        assert config.use_cache is True

    def test_from_env_proxies(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_PROXIES", "socks5://u:p@h:1080,http://h2:8080")
        config = LatebraConfig.from_env()
        assert len(config.proxies) == 2

    def test_from_env_captcha_keys(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_2CAPTCHA_KEY", "abc123")
        monkeypatch.setenv("LATEBRA_CAPSOLVER_KEY", "def456")
        config = LatebraConfig.from_env()
        assert config.two_captcha_key == "abc123"
        assert config.capsolver_key == "def456"

    def test_from_env_stealth_disabled_false(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_STEALTH_ENABLED", "false")
        config = LatebraConfig.from_env()
        assert config.stealth_enabled is False

    def test_from_env_stealth_disabled_zero(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_STEALTH_ENABLED", "0")
        config = LatebraConfig.from_env()
        assert config.stealth_enabled is False

    def test_from_env_timeout(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_REQUEST_TIMEOUT", "45.5")
        config = LatebraConfig.from_env()
        assert config.request_timeout == 45.5

    def test_from_env_log_level(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_LOG_LEVEL", "DEBUG")
        config = LatebraConfig.from_env()
        assert config.log_level == "DEBUG"

    def test_from_env_cache(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_CACHE_ENABLED", "0")
        config = LatebraConfig.from_env()
        assert config.use_cache is False

    def test_cache_dir_expansion(self, monkeypatch):
        monkeypatch.setenv("LATEBRA_CACHE_DIR", "~/custom/cache")
        config = LatebraConfig.from_env()
        assert config.cache_dir == os.path.expanduser("~/custom/cache")

    def test_search_backend_default(self):
        """Config should have search_backend default to 'auto'."""
        config = LatebraConfig()
        assert config.search_backend == "auto"

    def test_search_backend_from_env(self, monkeypatch):
        """Config should read search_backend from env."""
        monkeypatch.setenv("LATEBRA_SEARCH_BACKEND", "built-in")
        config = LatebraConfig.from_env()
        assert config.search_backend == "built-in"
