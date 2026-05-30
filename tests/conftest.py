"""Pytest configuration and fixtures for latebra tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_html() -> str:
    return """<!DOCTYPE html>
<html><head><title>Test Page</title></head>
<body>
<h1>Hello</h1>
<p>This is a test page for scraping.</p>
<ul>
<li>Item 1</li>
<li>Item 2</li>
<li>Item 3</li>
</ul>
</body>
</html>"""


@pytest.fixture
def blocked_html() -> str:
    return """<!DOCTYPE html>
<html><head><title>Access Denied</title></head>
<body>
<h1>Blocked</h1>
<p>Your request has been blocked.</p>
</body>
</html>"""
