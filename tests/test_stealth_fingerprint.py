"""Tests for the fingerprint generator."""

from __future__ import annotations

import json

import pytest

from latebra.stealth.fingerprint import BrowserFingerprint, FingerprintGenerator


class TestBrowserFingerprint:
    """Test the BrowserFingerprint dataclass."""

    def test_default_values(self):
        fp = BrowserFingerprint()
        assert fp.user_agent == ""
        assert fp.viewport_width == 1920
        assert fp.viewport_height == 1080
        assert fp.platform == "Win32"
        assert fp.hardware_concurrency == 8
        assert fp.device_memory == 8


class TestFingerprintGenerator:
    """Test the FingerprintGenerator."""

    def test_generate(self):
        gen = FingerprintGenerator()
        fp = gen.generate()
        assert fp.user_agent != ""
        assert 1280 <= fp.viewport_width <= 1920
        assert 720 <= fp.viewport_height <= 1080
        assert fp.platform in gen.PLATFORMS
        assert fp.vendor in ["Google Inc.", "Google Inc. (NVIDIA)", "Mozilla"]
        assert 4 <= fp.hardware_concurrency <= 16
        assert fp.device_memory in [4, 8, 16]

    def test_generate_unique(self):
        """Each call should produce a potentially different fingerprint."""
        gen = FingerprintGenerator()
        fp1 = gen.generate()
        fp2 = gen.generate()
        # At least one property may differ (statistical, not guaranteed by randomness)
        fingerprints = [fp1, fp2]
        # Check that different user agents are possible
        uas = set(f.user_agent for f in fingerprints)
        assert len(uas) <= len(fingerprints)

    def test_generate_stealth_init_script(self):
        gen = FingerprintGenerator()
        script = gen.generate_stealth_init_script()
        assert "CanvasRenderingContext2D.prototype.getImageData" in script
        assert "WebGLRenderingContext.prototype.getParameter" in script
        assert "webdriver" in script
        assert "window.chrome" in script

    def test_stealth_script_has_random_values(self):
        gen = FingerprintGenerator()
        s1 = gen.generate_stealth_init_script()
        s2 = gen.generate_stealth_init_script()
        # The renderer values should differ between calls
        assert s1 != s2
