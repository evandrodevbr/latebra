"""Tests for the human behavior simulator."""

from __future__ import annotations

import pytest

from latebra.stealth.behavior import BehaviorSimulator


class TestBehaviorSimulator:
    """Test the behavior simulation utilities."""

    def test_bezier_curve_length(self):
        points = BehaviorSimulator.bezier_curve(0, 0, 100, 100, steps=20)
        assert len(points) == 21
        assert points[0] == (0, 0)
        assert points[-1] == (100, 100)

    def test_bezier_curve_continuity(self):
        points = BehaviorSimulator.bezier_curve(10, 20, 300, 400)
        assert len(points) >= 5
        # First point should be start
        x0, y0 = points[0]
        assert abs(x0 - 10) < 1
        assert abs(y0 - 20) < 1
        # Last should be end
        xn, yn = points[-1]
        assert abs(xn - 300) < 1
        assert abs(yn - 400) < 1

    def test_random_delay_range(self):
        delay = BehaviorSimulator.random_delay(100, 200)
        assert 0.08 <= delay <= 0.23  # ms -> seconds with jitter

    def test_random_delay_min_only(self):
        delay = BehaviorSimulator.random_delay(min_ms=50)
        assert delay >= 0.04  # at least 50ms - 10% jitter

    def test_random_scroll_distance(self):
        for _ in range(100):
            d = BehaviorSimulator.random_scroll_distance()
            assert 10 <= d <= 800

    def test_random_typing_delay(self):
        for _ in range(50):
            d = BehaviorSimulator.random_typing_delay()
            assert 0.03 <= d <= 0.15
