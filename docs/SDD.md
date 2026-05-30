# latebra SDD — Spec-Driven Development Plan

## Overview
latebra MCP server implements the 7 anti-bot evasion techniques from the research document into a cohesive, multi-layer pipeline focused on maximum anonymity.

## Components (SDD Units)

### 1. Request Layer (curl_cffi)
**File:** `src/latebra/layers/request.py`
**Spec:**
- Use curl_cffi to impersonate Chrome 120+ TLS fingerprint
- Support rotating proxies (SOCKS5/HTTP)
- Random delays 2-8s between requests (rate limiting)
- Return raw HTML or raise BlockedError

### 2. Browser Layer (Patchright)
**File:** `src/latebra/layers/browser.py`
**Spec:**
- Patchright as primary (CDP stealth patches)
- Camoufox as fallback (Firefox stealth)
- nodriver as last resort (no chromedriver)
- Headless with randomized viewport/locale/timezone
- Wait for networkidle before returning content

### 3. Extraction Layer (Crawl4AI)
**File:** `src/latebra/layers/extraction.py`
**Spec:**
- Convert HTML → clean markdown
- CSS selectors + XPath for structured data
- Deduplication of repeated content
- SQLite cache (avoid re-scraping same URL within TTL)

### 4. Proxy Manager
**File:** `src/latebra/proxy/manager.py`
**Spec:**
- Rotate proxy on detection
- Track which IPs are banned per domain
- Support SOCKS5, HTTP proxies
- Circuit breaker: ban IP after N failures

### 5. Stealth Fingerprint
**File:** `src/latebra/stealth/fingerprint.py`
**Spec:**
- Randomize viewport, user-agent, locale, timezone
- Canvas/WebGL/AudioContext noise injection
- WebGL vendor randomization

### 6. Behavioral Simulation
**File:** `src/latebra/stealth/behavior.py`
**Spec:**
- Simulate mouse movements (non-linear)
- Natural scroll patterns
- Randomized action timing
- Human-like navigation flow

### 7. CAPTCHA Solver
**File:** `src/latebra/captcha/solver.py`
**Spec:**
- Interface for 2captcha/capsolver
- Auto-detect CAPTCHA presence
- Async solving with retry

### 8. Pipeline Orchestrator
**File:** `src/latebra/pipeline.py`
**Spec:**
- Try Layer 1 → if blocked, Layer 2 → if CAPTCHA, solve → if IP banned, rotate
- Return structured ScrapeResult with metadata
- Log each step for debugging

## Testing Strategy
- Unit tests for each component with mocked external deps
- Integration tests for pipeline orchestration
- pytest-asyncio for async test support
- Fixtures for proxy list, browser contexts

## SDD → TDD → Implementation
1. [SDD] Component specs (this document)
2. [TDD] Write tests first
3. [Impl] Implement passing code
4. [Review] Code review pass
5. [Verify] Run full test suite
