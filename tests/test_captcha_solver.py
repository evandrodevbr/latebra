"""Tests for the CAPTCHA solver."""

from __future__ import annotations

import pytest

from latebra.captcha.solver import CaptchaResult, CaptchaSolver


class TestCaptchaResult:
    """Test the CaptchaResult dataclass."""

    def test_default_values(self):
        r = CaptchaResult()
        assert r.token == ""
        assert r.service == ""
        assert r.error is None
        assert r.cost == 0.0
        assert r.timing_ms == 0.0


class TestCaptchaSolver:
    """Test the CaptchaSolver configuration and error handling."""

    def test_init_no_keys(self):
        solver = CaptchaSolver()
        assert solver.two_captcha_key is None
        assert solver.capsolver_key is None

    def test_init_with_keys(self):
        solver = CaptchaSolver(
            two_captcha_key="test_key_123",
            capsolver_key="test_capsolver_456",
        )
        assert solver.two_captcha_key == "test_key_123"
        assert solver.capsolver_key == "test_capsolver_456"

    @pytest.mark.asyncio
    async def test_solve_no_key(self):
        solver = CaptchaSolver()
        result = await solver.solve_recaptcha_v2(
            site_key="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
            page_url="http://example.com",
            service="2captcha",
        )
        assert result.error == "2captcha API key not configured"
        assert result.token == ""

    @pytest.mark.asyncio
    async def test_solve_capsolver_no_key(self):
        solver = CaptchaSolver()
        result = await solver.solve_recaptcha_v2(
            site_key="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
            page_url="http://example.com",
            service="capsolver",
        )
        assert result.error == "Capsolver API key not configured"
        assert result.token == ""
