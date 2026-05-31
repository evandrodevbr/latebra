# Performance & Observability Audit — latebra v0.2.0

**Date:** 2026-05-30
**Auditor:** Hermes Agent (direct review)
**Scope:** All 15 source files in `src/latebra/`

---

## Executive Summary

The codebase has **acceptable performance for a single-user MCP server** but will degrade under concurrent load. Connection pooling is absent for the HTTP request layer, CAPTCHA polling blocks event loop unnecessarily, and the pipeline retries serially without parallelism. **8 findings: 0 Critical, 3 High, 4 Medium, 1 Low.**

---

## Findings

### [HIGH] P1 — No Connection Pooling in Request Layer

**File:** `layers/request.py:46-65`
**Severity:** High
**Category:** I/O Efficiency

**Description:** `AsyncRequestLayer` creates one `AsyncSession` for curl_cffi or one `httpx.AsyncClient` for the fallback, shared for all requests. While this is technically a persistent connection, the implementation:
- Never configures connection pool limits (`httpx` defaults to 100 connections in the pool, but curl_cffi session does not reuse connections efficiently)
- Has no keep-alive configuration
- Never closes idle connections

**Impact:** Under moderate concurrency (5+ simultaneous scrapes), TCP connection churn increases latency by 50-200ms per request.

**Fix:**
```python
self._session = httpx.AsyncClient(
    timeout=self.timeout,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    ...
)
```

---

### [HIGH] P2 — Serial CAPTCHA Polling Blocks Event Loop

**File:** `captcha/solver.py:84-101`, `captcha/solver.py:138-150`
**Severity:** High
**Category:** Async Efficiency

**Description:** CAPTCHA solving uses `for _ in range(60): await asyncio.sleep(5)` — this is 60 sequential `sleep` calls that block the coroutine for up to 5 minutes. While `asyncio.sleep` doesn't block the event loop, a single CAPTCHA solve ties up the coroutine for 5 minutes. Two concurrent CAPTCHA requests would each take 5 minutes (not total, but individually).

**Why this matters:** The MCP server uses a single event loop. A long-running CAPTCHA solve prevents other requests from being processed (they're not truly concurrent because the coroutine is occupied).

**Fix:** Use `asyncio.wait_for` with timeout, or break polling into a background task:
```python
async def _poll_with_timeout(self, task_id, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = await self._check_result(task_id)
        if result:
            return result
        await asyncio.sleep(min(5, deadline - time.monotonic()))
    raise TimeoutError("CAPTCHA solve timed out")
```

---

### [HIGH] P3 — Pipeline Retries Serially, Not in Parallel

**File:** `pipeline.py:76-158`
**Severity:** High
**Category:** Latency

**Description:** The pipeline tries `curl_cffi` → `patchright` → `camoufox` → `nodriver` sequentially. Each step takes 5-30 seconds. A site that blocks curl_cffi but works with nodriver will always take 45+ seconds (curl_cffi timeout + patchright startup + camoufox startup).

**Recommendation:** For latency-sensitive use cases, offer a "parallel probe" mode where the first 2 layers run simultaneously, and the first successful response is used.

---

### [MEDIUM] P4 — Browser Startup Costs Not Amortized

**File:** `layers/browser.py:95-98`
**Severity:** Medium
**Category:** Startup Overhead

**Description:** Every `_scrape_patchright()` call creates a new browser process (`p.chromium.launch(headless=True)`) and tears it down (`browser.close()`). Browser startup alone costs 1-3 seconds.

**Recommendation:** Pool browser instances for reuse across requests:
```python
class BrowserPool:
    def __init__(self, max_browsers=3):
        self._pool: list[Browser] = []
        self._sem = asyncio.Semaphore(max_browsers)

    async def acquire(self):
        async with self._sem:
            if self._pool:
                return self._pool.pop()
            return await self._launch_new()
```

---

### [MEDIUM] P5 — SQLite Cache Access Performed Synchronously

**File:** `layers/extraction.py:63-86`
**Severity:** Medium
**Category:** I/O Blocking

**Description:** `ContentCache.get()` and `ContentCache.set()` perform synchronous SQLite I/O (`cur.fetchone()`, `conn.commit()`) on the event loop thread. SQLite queries typically take <1ms, but under I/O pressure (slow disk, high cache churn), this blocks the event loop.

**Recommendation:** Use `aiosqlite` for async SQLite access, or run cache operations in `asyncio.to_thread()`:
```python
async def get_async(self, url, selector=None, ttl=3600):
    return await asyncio.to_thread(self.get, url, selector, ttl)
```

---

### [MEDIUM] P6 — No Timeout on Extraction Cache Operations

**File:** `layers/extraction.py:63-86`
**Severity:** Medium
**Category:** Timeout Configuration

**Description:** Cache reads/writes have no timeout — a locked or corrupted SQLite database would hang indefinitely.

**Fix:** Add timeout wrapper to all SQLite operations.

---

### [MEDIUM] P7 — Crawl4AI Instantiated Per-Extraction

**File:** `layers/extraction.py:144-145`
**Severity:** Medium
**Category:** Resource Allocation

**Description:** `async with AsyncWebCrawler() as crawler:` creates a new crawler instance for every extraction. Crawl4AI internally creates browser contexts, which are expensive.

**Recommendation:** Pool `AsyncWebCrawler` instances or use session-level caching.

---

### [LOW] P8 — No Metrics/Telemetry

**Files:** All modules
**Severity:** Low
**Category:** Observability

**Description:** The application has no metrics, tracing, or performance counters beyond basic `timing_ms` fields on result dataclasses. There's no way to measure:
- Requests per second
- Success rate per layer
- Average latency per layer
- Cache hit rate
- Proxy failure rate over time

**Recommendation:** Add `structlog` with structured logging for key metrics, or expose a `latebra_metrics` MCP resource.

---

## Summary

| Severity | Count | Focus |
|----------|-------|-------|
| Critical | 0 | — |
| High | 3 | No connection pooling, serial CAPTCHA polling, serial pipeline |
| Medium | 4 | Browser startup costs, sync SQLite, no cache timeout, Crawl4AI per-extraction |
| Low | 1 | No observability/metrics |

---

## Recommended Actions

1. **High priority:** Configure httpx connection limits, consider parallel pipeline probing for latency-critical use cases
2. **Before production:** Pool browser instances, use `aiosqlite` for async cache, add circuit breaker to CAPTCHA solver
3. **Observability:** Add structured metrics and expose via MCP resource
