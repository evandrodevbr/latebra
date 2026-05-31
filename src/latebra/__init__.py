"""latebra - MCP server for anti-bot web scraping with maximum anonymity.

Multi-layer evasion pipeline:
  Layer 1 (HTTP): curl_cffi + TLS impersonation + rotating proxies
  Layer 2 (Browser): Patchright → Camoufox → nodriver fallback chain
  Layer 3 (Extraction): Crawl4AI + CSS/XPath + dedup + SQLite cache
"""

from latebra.config import LatebraConfig
from latebra.constants import (
    DETECTION_MARKERS,
    MIN_CONTENT_LENGTH,
    PREVIEW_MAX_LENGTH,
)
from latebra.pipeline import ScrapeResult, SmartScrapePipeline
from latebra.server import LatebraServer, serve
from latebra.validation import validate

__version__ = "0.2.0"

__all__ = [
    "LatebraConfig",
    "LatebraServer",
    "ScrapeResult",
    "SmartScrapePipeline",
    "DETECTION_MARKERS",
    "MIN_CONTENT_LENGTH",
    "PREVIEW_MAX_LENGTH",
    "serve",
    "validate",
]
