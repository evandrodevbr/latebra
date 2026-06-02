"""Tests for the MCP server."""

from __future__ import annotations

import json

import pytest

from latebra.server import LatebraServer


class TestLatebraServer:
    """Test the LatebraServer tool definitions and formatting."""

    def test_init(self):
        server = LatebraServer()
        assert server.pipeline is not None

    def test_init_with_options(self):
        server = LatebraServer(
            proxies=["http://proxy1:8080"],
            two_captcha_key="test_2captcha",
        )
        assert server.pipeline is not None

    def test_tool_definitions_three_tools(self):
        server = LatebraServer()
        tools = server.tool_definitions
        assert len(tools) == 8  # +get_log_path

    def test_tool_definitions_names(self):
        server = LatebraServer()
        names = [t["name"] for t in server.tool_definitions]
        assert "latebra_scrape" in names
        assert "latebra_scrape_with_browser" in names
        assert "latebra_check_anonymity" in names

    def test_handle_unknown_tool(self):
        import pytest
        server = LatebraServer()
        with pytest.raises(ValueError, match="Unknown tool"):
            import asyncio
            asyncio.run(server.handle_tool("unknown_tool", {}))

    def test_format_result_with_content(self):
        from latebra.pipeline import ScrapeResult
        server = LatebraServer()
        result = ScrapeResult(
            url="http://example.com",
            status="success",
            content="<html>" + "x" * 1000,
            content_length=1000,
            layer_used="request",
            title="Test",
        )
        formatted = server._format_result(result)
        assert formatted["url"] == "http://example.com"
        assert formatted["status"] == "success"
        assert formatted["content_preview"].endswith("...")
        assert formatted["title"] == "Test"

    def test_search_backend_config(self):
        """Server should pass search_backend to SearchLayer."""
        from latebra.config import LatebraConfig

        config = LatebraConfig(search_backend="built-in")
        server = LatebraServer(config=config)
        assert server.search.search_backend == "built-in"
