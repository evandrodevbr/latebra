"""MCP server entry point for latebra.

Exposes MCP tools for each anti-bot evasion layer.
"""

from __future__ import annotations

import json
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from latebra.pipeline import SmartScrapePipeline

logger = logging.getLogger("latebra")


async def serve() -> None:
    """Run the MCP server with latebra tools."""
    server = Server("latebra")
    pipeline = SmartScrapePipeline()

    @server.list_tools()
    async def list_tools() -> list:
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
                        },
                    },
                    "required": ["url"],
                },
            },
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        if name == "latebra_scrape":
            result = await pipeline.scrape(arguments["url"])
            return [{"type": "text", "text": json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}]
        elif name == "latebra_scrape_with_browser":
            result = await pipeline.scrape_with_browser(
                arguments["url"],
                browser=arguments.get("browser", "patchright"),
            )
            return [{"type": "text", "text": json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}]
        elif name == "latebra_check_anonymity":
            result = await pipeline.check_anonymity(arguments["url"])
            return [{"type": "text", "text": json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}]
        else:
            raise ValueError(f"Unknown tool: {name}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="latebra",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
