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

from latebra.constants import PREVIEW_MAX_LENGTH
from latebra.pipeline import SmartScrapePipeline, ScrapeResult
from latebra.layers.search import SearchLayer, DEFAULT_SEARXNG_URL
from latebra.layers.crawler import CrawlerLayer
from latebra.layers.interact import InteractLayer

logger = logging.getLogger("latebra")


class LatebraServer:
    """MCP-compatible server for latebra anti-bot scraping."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        two_captcha_key: str | None = None,
        capsolver_key: str | None = None,
        searxng_url: str = DEFAULT_SEARXNG_URL,
    ) -> None:
        self.pipeline = SmartScrapePipeline(
            proxies=proxies,
            two_captcha_key=two_captcha_key,
            capsolver_key=capsolver_key,
        )
        self.search = SearchLayer(base_url=searxng_url)
        self.crawler = CrawlerLayer(max_depth=2, max_pages=20)
        self.interact = InteractLayer()

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
            {
                "name": "latebra_search",
                "description": "Search the web using a self-hosted SearXNG instance. "
                               "Returns titles, URLs, and snippets.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "latebra_crawl",
                "description": "Crawl a website starting from a seed URL. "
                               "Follows links up to a configured depth and page limit.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Seed URL to start crawling from",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum crawl depth",
                            "default": 1,
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Maximum pages to crawl",
                            "default": 10,
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "latebra_batch_scrape",
                "description": "Scrape multiple URLs concurrently with a configurable concurrency limit.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of URLs to scrape",
                        },
                        "max_concurrent": {
                            "type": "integer",
                            "description": "Maximum simultaneous requests",
                            "default": 5,
                        },
                    },
                    "required": ["urls"],
                },
            },
            {
                "name": "latebra_interact",
                "description": "Interact with a web page — navigate, click elements, or type text.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["navigate", "click", "type"],
                            "description": "Interaction type",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to (for 'navigate' action)",
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS selector (for 'click' and 'type' actions)",
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to type (for 'type' action)",
                        },
                    },
                    "required": ["action"],
                },
            },
        ]

    async def handle_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle a tool call via dispatch dict."""
        dispatch = {
            "latebra_scrape": self._handle_scrape,
            "latebra_scrape_with_browser": self._handle_scrape_with_browser,
            "latebra_check_anonymity": self._handle_check_anonymity,
            "latebra_search": self._handle_search,
            "latebra_crawl": self._handle_crawl,
            "latebra_batch_scrape": self._handle_batch_scrape,
            "latebra_interact": self._handle_interact,
        }
        handler = dispatch.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        return await handler(arguments)

    async def _handle_scrape(self, args: dict[str, Any]) -> dict[str, Any]:
        result = await self.pipeline.scrape(args["url"])
        return self._format_result(result)

    async def _handle_scrape_with_browser(self, args: dict[str, Any]) -> dict[str, Any]:
        result = await self.pipeline.scrape_with_browser(
            args["url"],
            browser=args.get("browser", "patchright"),
        )
        return self._format_result(result)

    async def _handle_check_anonymity(self, args: dict[str, Any]) -> dict[str, Any]:
        url = args.get("url", "https://httpbin.org/headers")
        result = await self.pipeline.check_anonymity(url)
        return result if isinstance(result, dict) else result.to_dict()

    async def _handle_search(self, args: dict[str, Any]) -> dict[str, Any]:
        results = await self.search.search(
            query=args["query"],
            max_results=args.get("max_results", 10),
        )
        return {"results": results, "total": len(results)}

    async def _handle_crawl(self, args: dict[str, Any]) -> dict[str, Any]:
        if args.get("max_depth") is not None or args.get("max_pages") is not None:
            self.crawler = CrawlerLayer(
                max_depth=args.get("max_depth", 2),
                max_pages=args.get("max_pages", 20),
            )
        pages = await self.crawler.crawl(args["url"])
        return {"pages": pages, "total": len(pages)}

    async def _handle_batch_scrape(self, args: dict[str, Any]) -> dict[str, Any]:
        results = await self.pipeline.batch_scrape(
            urls=args["urls"],
            max_concurrent=args.get("max_concurrent", 5),
        )
        return {
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "successful": sum(1 for r in results if r.status == "success"),
        }

    async def _handle_interact(self, args: dict[str, Any]) -> dict[str, Any]:
        action = args["action"]
        if action == "navigate":
            return await self.interact.navigate(args["url"])
        elif action == "click":
            return await self.interact.click(args.get("selector", "a"))
        elif action == "type":
            return await self.interact.type_text(
                args.get("selector", "input"),
                args.get("text", ""),
            )
        return {"error": f"Unknown action: {action}"}

    def _format_result(self, result: ScrapeResult) -> dict[str, Any]:
        """Format ScrapeResult for JSON response."""
        base = result.to_dict()
        base["content_preview"] = (
            result.content[:PREVIEW_MAX_LENGTH] + "..." if result.content and len(result.content) > PREVIEW_MAX_LENGTH
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
