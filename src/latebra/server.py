"""MCP server entry point for latebra.

Exposes MCP tools for each anti-bot evasion layer.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from latebra.pipeline import SmartScrapePipeline, ScrapeResult

logger = logging.getLogger("latebra")


class LatebraServer:
    """MCP-compatible server for latebra anti-bot scraping."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        two_captcha_key: str | None = None,
        capsolver_key: str | None = None,
    ) -> None:
        self.pipeline = SmartScrapePipeline(
            proxies=proxies,
            two_captcha_key=two_captcha_key,
            capsolver_key=capsolver_key,
        )

    @property
    def tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "latebra_scrape",
                "description": "Scrape a URL using the multi-layer anti-bot evasion pipeline. "
                               "Automatically tries curl_cffi first, then falls back to browser.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Target URL to scrape",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "latebra_scrape_with_browser",
                "description": "Scrape a URL forcing browser mode (Patchright/Camoufox).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target URL"},
                        "browser": {
                            "type": "string",
                            "enum": ["patchright", "camoufox", "nodriver"],
                            "description": "Browser engine to use",
                            "default": "patchright",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "latebra_check_anonymity",
                "description": "Test current anonymity level against known detection services.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to test against (e.g., https://browserscan.net)",
                            "default": "https://httpbin.org/headers",
                        },
                    },
                },
            },
        ]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle a tool call and return MCP-formatted result."""
        if name == "latebra_scrape":
            result = await self.pipeline.scrape(arguments["url"])
            return self._format_result(result)
        elif name == "latebra_scrape_with_browser":
            result = await self.pipeline.scrape_with_browser(
                arguments["url"],
                browser=arguments.get("browser", "patchright"),
            )
            return self._format_result(result)
        elif name == "latebra_check_anonymity":
            url = arguments.get("url", "https://httpbin.org/headers")
            result = await self.pipeline.check_anonymity(url)
            if hasattr(result, "to_dict"):
                return result.to_dict()  # type: ignore
            return result  # type: ignore
        else:
            raise ValueError(f"Unknown tool: {name}")

    def _format_result(self, result: ScrapeResult) -> dict[str, Any]:
        """Format ScrapeResult for JSON response."""
        base = result.to_dict()
        base["content_preview"] = (
            result.content[:500] + "..." if result.content and len(result.content) > 500
            else result.content or ""
        )
        return base


async def serve() -> None:
    """Run the MCP server with latebra tools."""
    mcp_server = Server("latebra")
    latebra = LatebraServer()

    @mcp_server.list_tools()
    async def list_tools() -> list:
        return latebra.tool_definitions

    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        result = await latebra.handle_tool(name, arguments)
        return [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="latebra",
                server_version="0.2.0",
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
