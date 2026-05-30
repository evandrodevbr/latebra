"""latebra - MCP server for anti-bot web scraping with maximum anonymity.

Multi-layer evasion pipeline:
  Layer 1 (HTTP): curl_cffi + TLS impersonation + rotating proxies
  Layer 2 (Browser): Patchright → Camoufox → nodriver fallback chain
  Layer 3 (Extraction): Crawl4AI + CSS/XPath + dedup + SQLite cache
"""

__version__ = "0.1.0"
