"""Human behavior simulation for browser interactions."""

from __future__ import annotations

import asyncio
import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class BehaviorSimulator:
    """Simulates human-like browsing behavior to evade detection."""

    @staticmethod
    def bezier_curve(
        start_x: float, start_y: float,
        end_x: float, end_y: float,
        steps: int = 20,
    ) -> list[tuple[float, float]]:
        """Generate bezier curve points for realistic mouse movement."""
        cp1_x = start_x + random.uniform(-50, 150)
        cp1_y = start_y + random.uniform(-50, 50)
        cp2_x = end_x + random.uniform(-50, 50)
        cp2_y = end_y + random.uniform(-50, 50)

        points = []
        for i in range(steps + 1):
            t = i / steps
            x = (
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * cp1_x
                + 3 * (1 - t) * t ** 2 * cp2_x
                + t ** 3 * end_x
            )
            y = (
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * cp1_y
                + 3 * (1 - t) * t ** 2 * cp2_y
                + t ** 3 * end_y
            )
            points.append((x, y))
        return points

    @staticmethod
    def random_delay(min_ms: int = 50, max_ms: int = 300) -> float:
        """Generate random delay with jitter."""
        base = random.uniform(min_ms, max_ms)
        jitter = random.uniform(-base * 0.1, base * 0.1)
        return (base + jitter) / 1000.0

    @staticmethod
    def random_scroll_distance() -> int:
        """Generate random scroll distance like a human."""
        return random.choice([
            random.randint(100, 400),  # normal scroll
            random.randint(500, 800),  # big scroll
            random.randint(10, 80),     # tiny adjustment
        ])

    @staticmethod
    def random_typing_delay() -> float:
        """Generate realistic typing delay between keystrokes."""
        return random.uniform(0.03, 0.15)

    async def simulate_mouse_movement(
        self,
        page: Any,
        start_x: float, start_y: float,
        end_x: float, end_y: float,
    ) -> None:
        """Simulate human-like mouse movement using bezier curves."""
        try:
            points = self.bezier_curve(start_x, start_y, end_x, end_y)
            for x, y in points:
                await page.mouse.move(x, y)
                await asyncio.sleep(self.random_delay(5, 20))
        except Exception as e:
            logger.warning("Mouse simulation failed: %s", e)

    async def simulate_scroll(self, page: Any, scrolls: int = 3) -> None:
        """Simulate human-like scrolling behavior."""
        try:
            for _ in range(scrolls):
                distance = self.random_scroll_distance()
                steps = random.randint(5, 15)
                step_size = distance / steps

                for _ in range(steps):
                    await page.evaluate(f"window.scrollBy(0, {step_size})")
                    await asyncio.sleep(self.random_delay(20, 80))

                pause = self.random_delay(500, 3000)
                await asyncio.sleep(pause)
        except Exception as e:
            logger.warning("Scroll simulation failed: %s", e)

    async def simulate_typing(self, page: Any, text: str, selector: str) -> None:
        """Simulate human-like typing into an input field."""
        try:
            await page.click(selector)
            await asyncio.sleep(random.uniform(0.2, 0.5))

            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(self.random_typing_delay())
        except Exception as e:
            logger.warning("Typing simulation failed: %s", e)

    async def simulate_wait_random(self) -> None:
        """Wait a random amount of time like a human reading."""
        await asyncio.sleep(random.uniform(1.0, 4.0))

    async def simulate_page_visit(
        self,
        page: Any,
        scroll: bool = True,
        mouse_move: bool = True,
        wait: bool = True,
    ) -> None:
        """Simulate a full human-like page visit."""
        if mouse_move:
            vp = await page.evaluate("({w: window.innerWidth, h: window.innerHeight})")
            if vp:
                sx, sy = random.uniform(0, vp["w"]), random.uniform(0, vp["h"])
                ex, ey = random.uniform(0, vp["w"]), random.uniform(0, vp["h"])
                await self.simulate_mouse_movement(page, sx, sy, ex, ey)

        if scroll:
            await self.simulate_scroll(page, random.randint(1, 4))

        if wait:
            await self.simulate_wait_random()
