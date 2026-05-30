"""Entry point to run the latebra MCP server.

Usage:
    python -m latebra run
    uvx latebra
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="latebra", description="Anti-bot scraping MCP server")
    parser.add_argument("command", nargs="?", default="run", help="Command (default: run)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if args.command == "run":
        from latebra.server import serve
        asyncio.run(serve())
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
