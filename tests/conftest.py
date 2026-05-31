"""Pytest fixtures for latebra tests."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest


SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Test Page</title></head>
<body><h1>Hello World</h1><p>This is a test page for scraping.</p>
<a href="http://example.com/link1">Link 1</a>
<a href="http://example.com/link2">Link 2</a>
</body></html>"""

BLOCKED_HTML = """<!DOCTYPE html>
<html><head><title>Blocked</title></head>
<body><h1>Access Denied</h1><p>Your request has been blocked.</p>
<p>Please complete the security check to access this site.</p>
</body></html>"""

CAPTCHA_HTML = """<!DOCTYPE html>
<html><head><title>Captcha Challenge</title></head>
<body>
<div class="g-recaptcha" data-sitekey="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></div>
<script src="https://www.google.com/recaptcha/api.js"></script>
</body></html>"""


@pytest.fixture
def sample_html() -> str:
    return SAMPLE_HTML


@pytest.fixture
def blocked_html() -> str:
    return BLOCKED_HTML


@pytest.fixture
def captcha_html() -> str:
    return CAPTCHA_HTML


@pytest.fixture
def proxies() -> list[str]:
    return [
        "socks5://user:pass@proxy1.example.com:1080",
        "http://user:pass@proxy2.example.com:3128",
    ]
