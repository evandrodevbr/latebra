# AGENTS.md — latebra Project

## Project Overview
latebra is an MCP server for anti-bot web scraping with maximum anonymity.
Implements a 3-layer evasion pipeline:
- Layer 1: curl_cffi (HTTP with TLS impersonation)
- Layer 2: Patchright → Camoufox → nodriver (browser stealth chain)
- Layer 3: Crawl4AI extraction + SQLite cache

## Tech Stack
- Python 3.12+
- MCP SDK (mcp>=1.0.0)
- curl_cffi, camoufox, patchright, nodriver, crawl4ai
- pytest, pytest-asyncio, ruff

## Architecture
src/latebra/
├── server.py       # MCP server entry (tools: scrape, scrape_with_browser, check_anonymity)
├── pipeline.py     # SmartScrapePipeline orchestrator
├── layers/
│   ├── request.py   # curl_cffi + proxy
│   ├── browser.py   # Patchright/Camoufox/nodriver
│   └── extraction.py # Crawl4AI
├── proxy/
│   └── manager.py   # Proxy rotation
├── stealth/
│   ├── fingerprint.py # Fingerprint randomization
│   └── behavior.py    # Behavioral simulation
└── captcha/
    └── solver.py    # 2captcha/capsolver integration

## Development Workflow
1. SDD first: Metis + Momus write spec for each component
2. TDD: write test, watch fail, write code to pass
3. Implementation: Sisyphus + Sisyphus-Junior
4. QA: workflow tdd + verification
5. Review: workflow pr-review

## Key Constraints
- Maximum anonymity: no hardcoded IPs, credentials, or identifiable data
- Async-first: all I/O must be async
- Graceful fallback: each layer failure should cascade to next
- All browser interactions must use stealth/anonymized profiles
