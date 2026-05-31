"""Tests for latebra.constants module — verify all constants are defined."""

from __future__ import annotations

from latebra import constants


class TestConstants:
    """Verify constant definitions are present and have expected types."""

    def test_content_thresholds(self):
        assert isinstance(constants.MIN_CONTENT_LENGTH, int)
        assert constants.MIN_CONTENT_LENGTH > 0
        assert isinstance(constants.PREVIEW_MAX_LENGTH, int)
        assert constants.PREVIEW_MAX_LENGTH > 0

    def test_captcha_polling(self):
        assert isinstance(constants.CAPTCHA_POLL_MAX_ATTEMPTS, int)
        assert constants.CAPTCHA_POLL_MAX_ATTEMPTS > 0
        assert isinstance(constants.CAPTCHA_POLL_INTERVAL_2CAPTCHA, int)
        assert isinstance(constants.CAPTCHA_POLL_INTERVAL_CAPSOLVER, int)

    def test_request_defaults(self):
        assert isinstance(constants.DEFAULT_REQUEST_TIMEOUT, float)
        assert constants.DEFAULT_REQUEST_TIMEOUT > 0
        assert isinstance(constants.DEFAULT_MAX_RETRIES, int)
        assert constants.DEFAULT_MAX_RETRIES >= 0

    def test_cache_defaults(self):
        assert isinstance(constants.DEFAULT_CACHE_TTL, int)
        assert constants.DEFAULT_CACHE_DIR == "~/.cache/latebra"

    def test_user_agents_not_empty(self):
        assert len(constants.USER_AGENTS) >= 3
        for ua in constants.USER_AGENTS:
            assert "Mozilla" in ua or "AppleWebKit" in ua

    def test_viewports_not_empty(self):
        assert len(constants.VIEWPORTS) >= 3
        for vp in constants.VIEWPORTS:
            assert len(vp) == 2
            assert vp[0] > 0 and vp[1] > 0

    def test_platforms_not_empty(self):
        assert len(constants.PLATFORMS) >= 2

    def test_impersonate_options(self):
        assert len(constants.IMPERSONATE_OPTIONS) >= 3
        for opt in constants.IMPERSONATE_OPTIONS:
            assert isinstance(opt, str)

    def test_engines_list(self):
        assert len(constants.ENGINES) >= 2

    def test_detection_markers(self):
        assert len(constants.DETECTION_MARKERS) >= 3
        for marker in constants.DETECTION_MARKERS:
            assert isinstance(marker, str)
            assert len(marker) > 0

    def test_noise_bounds(self):
        assert 0 < constants.CANVAS_NOISE_MIN < constants.CANVAS_NOISE_MAX
        assert 0 < constants.AUDIO_NOISE_MIN < constants.AUDIO_NOISE_MAX

    def test_hardware_options(self):
        assert len(constants.HARDWARE_CONCURRENCY_OPTIONS) >= 3
        assert len(constants.DEVICE_MEMORY_OPTIONS) >= 2
        assert len(constants.DEVICE_SCALE_FACTORS) >= 2

    def test_proxy_circuit_breaker(self):
        assert isinstance(constants.PROXY_MAX_FAILURES, int)
        assert isinstance(constants.PROXY_COOLDOWN_BASE, int)
        assert isinstance(constants.PROXY_COOLDOWN_MAX, int)
