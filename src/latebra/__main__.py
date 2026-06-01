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

    # Initialize file logging (cross-platform, rotating)
    from latebra.log_utils import setup_file_logging, get_log_path
    setup_file_logging()
    logging.getLogger("latebra").info("File logging initialized — logs at: %s", get_log_path())

    # Capture uncaught exceptions
    def _excepthook(typ, val, tb) -> None:
        logging.getLogger("latebra").critical(
            "Uncaught %s: %s", typ.__name__, val, exc_info=(typ, val, tb)
        )
    sys.excepthook = _excepthook

    if args.command == "run":
        from latebra.server import serve
        asyncio.run(serve())
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
