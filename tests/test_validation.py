"""Tests for latebra.validation module — URL validation and SSRF protection."""

from __future__ import annotations

import pytest

from latebra.validation import validate


class TestValidateUrl:
    """Test URL validation for safe scraping."""

    # ── Valid URLs ────────────────────────────────
    def test_valid_http(self):
        assert validate("http://example.com") == "http://example.com"

    def test_valid_https(self):
        assert validate("https://example.com/path?q=1") == "https://example.com/path?q=1"

    def test_valid_with_port(self):
        assert validate("https://example.com:8443/path") == "https://example.com:8443/path"

    def test_strips_fragment(self):
        result = validate("https://example.com/page#section")
        assert "#" not in result

    # ── Invalid schemes ───────────────────────────
    def test_rejects_file_scheme(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate("ftp://example.com")

    # ── SSRF: Blocked hostnames ───────────────────
    def test_rejects_localhost(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://localhost")

    def test_rejects_localhost_with_port(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://localhost:8080")

    # ── SSRF: Private IPs ─────────────────────────
    def test_rejects_10_x(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://10.0.0.1")

    def test_rejects_172_16_x(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://172.16.0.1")

    def test_rejects_192_168_x(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://192.168.1.1")

    def test_rejects_127_x(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://127.0.0.1")

    def test_rejects_169_254_x(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://169.254.1.1")

    # ── SSRF: Metadata endpoint ───────────────────
    def test_rejects_aws_metadata(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://169.254.169.254/latest/meta-data/")

    # ── Edge cases ────────────────────────────────
    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate("")

    def test_rejects_no_hostname(self):
        with pytest.raises(ValueError, match="hostname"):
            validate("https:///path")

    def test_case_insensitive_scheme(self):
        result = validate("HTTPS://Example.COM")
        assert result.startswith("https://")

    def test_0_0_0_0_rejected(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://0.0.0.0")

    def test_cgnat_rejected(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://100.64.0.1")

    def test_ipv6_loopback_rejected(self):
        with pytest.raises(ValueError, match="blocked"):
            validate("http://[::1]")
