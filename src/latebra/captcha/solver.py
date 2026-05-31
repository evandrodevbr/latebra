"""CAPTCHA solving integration for 2captcha and capsolver services."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CaptchaResult:
    token: str = ""
    service: str = ""
    error: str | None = None
    cost: float = 0.0
    timing_ms: float = 0.0


class CaptchaSolver:
    """Unified CAPTCHA solving service integration."""

    def __init__(
        self,
        two_captcha_key: str | None = None,
        capsolver_key: str | None = None,
    ):
        self.two_captcha_key = two_captcha_key
        self.capsolver_key = capsolver_key
        self._client = httpx.AsyncClient(timeout=60)

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        service: str = "2captcha",
    ) -> CaptchaResult:
        """Solve reCAPTCHA v2 using specified service."""
        result = CaptchaResult(service=service)
        start = asyncio.get_event_loop().time()

        if service == "2captcha":
            result = await self._solve_2captcha(site_key, page_url, result)
        elif service == "capsolver":
            result = await self._solve_capsolver(site_key, page_url, result)

        result.timing_ms = (asyncio.get_event_loop().time() - start) * 1000
        return result

    async def _solve_2captcha(
        self,
        site_key: str,
        page_url: str,
        result: CaptchaResult,
    ) -> CaptchaResult:
        if not self.two_captcha_key:
            result.error = "2captcha API key not configured"
            return result

        try:
            # Submit captcha
            resp = await self._client.post(
                "https://2captcha.com/in.php",
                params={
                    "key": self.two_captcha_key,
                    "method": "userrecaptcha",
                    "googlekey": site_key,
                    "pageurl": page_url,
                    "json": 1,
                },
            )
            data = resp.json()
            if data.get("status") != 1:
                result.error = f"2captcha submit failed: {data.get('request', 'unknown')}"
                return result

            captcha_id = data["request"]

            # Poll for result
            for _ in range(60):
                await asyncio.sleep(5)
                poll = await self._client.post(
                    "https://2captcha.com/res.php",
                    params={
                        "key": self.two_captcha_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1,
                    },
                )
                poll_data = poll.json()
                if poll_data.get("status") == 1:
                    result.token = poll_data["request"]
                    return result
                if poll_data.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    result.error = "CAPTCHA unsolvable"
                    return result

            result.error = "2captcha timeout after 5 minutes"

        except Exception as e:
            result.error = f"2captcha error: {e}"

        return result

    async def _solve_capsolver(
        self,
        site_key: str,
        page_url: str,
        result: CaptchaResult,
    ) -> CaptchaResult:
        if not self.capsolver_key:
            result.error = "Capsolver API key not configured"
            return result

        try:
            resp = await self._client.post(
                "https://api.capsolver.com/createTask",
                json={
                    "clientKey": self.capsolver_key,
                    "task": {
                        "type": "ReCaptchaV2TaskProxyLess",
                        "websiteKey": site_key,
                        "websiteURL": page_url,
                    },
                },
            )
            data = resp.json()
            task_id = data.get("taskId")
            if not task_id:
                result.error = f"capsolver create failed: {data}"
                return result

            for _ in range(60):
                await asyncio.sleep(3)
                poll = await self._client.post(
                    "https://api.capsolver.com/getTaskResult",
                    json={
                        "clientKey": self.capsolver_key,
                        "taskId": task_id,
                    },
                )
                poll_data = poll.json()
                if poll_data.get("status") == "ready":
                    result.token = poll_data["solution"]["gRecaptchaResponse"]
                    return result

            result.error = "capsolver timeout after 3 minutes"

        except Exception as e:
            result.error = f"capsolver error: {e}"

        return result

    async def close(self):
        await self._client.aclose()
