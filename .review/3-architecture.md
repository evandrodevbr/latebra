# Architecture Audit Report — latebra v0.2.0

**Date:** 2026-05-30
**Auditor:** Hermes Agent (direct review)
**Scope:** All 15 source files in `src/latebra/` + `pyproject.toml`

---

## Executive Summary

The 3-layer architecture (Request → Browser → Extraction) is **well-designed and maps cleanly to the anti-bot problem domain**. However, the MCP server layer has tight coupling to the pipeline, no input validation exists, and component boundaries are blurred by shared mutable state. **7 findings: 1 Critical, 3 High, 2 Medium, 1 Low.**

---

## Architecture Diagram

```
┌──────────────────────────────────────┐
│          MCP Server (stdio)          │
│  latebra_scrape / _with_browser /    │
│  _check_anonymity                    │
└──────────────┬───────────────────────┘
               │ (tight coupling)
┌──────────────▼───────────────────────┐
│       SmartScrapePipeline            │
│  Orchestrates 3-layer flow           │
│  + proxy rotation + captcha solving  │
└──┬──────────┬──────────┬─────────────┘
   │          │          │
┌──▼───┐ ┌───▼────┐ ┌──▼──────────┐
│Layer1│ │Layer2  │ │Layer3       │
│Request│ │Browser │ │Extraction   │
│curl  │ │Patchr  │ │Crawl4AI     │
│cffi  │ │Camouf  │ │+ Cache(SQL) │
│      │ │nodriver│ │             │
└──────┘ └────────┘ └─────────────┘
   │          │          │
┌──▼──────────▼──────────▼────────────┐
│     Cross-Cutting Concerns          │
│  ProxyManager  BehaviorSimulator    │
│  CaptchaSolver  FingerprintGen      │
└─────────────────────────────────────┘
```

---

## Findings

### [CRITICAL] A1 — No Input Validation Layer — SSRF Attack Surface

**Files:** `server.py:47-51`, `server.py:61-62`, `server.py:78-80`
**Severity:** Critical
**Category:** Security Architecture

**Description:** The MCP server accepts arbitrary URL strings with zero validation before passing them to the pipeline. Every tool call is a potential SSRF vector. An architectural validation layer must exist BEFORE any request is made.

**Why this is architectural:** Input validation is a cross-cutting concern that belongs at the server boundary, not scattered across layers. Currently, no component owns validation — every layer trusts the input blindly.

**Recommendation:**
```python
# New module: src/latebra/validation.py
class URLValidator:
    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_HOSTS = {"localhost", "127.0.0.1", "169.254.169.254", ...}
    BLOCKED_NETWORKS = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ...
    ]
    
    def validate(self, url: str) -> str:  # returns sanitized URL or raises
        ...
```

Integrate at `server.py` handler level before pipeline dispatch.

---

### [HIGH] A2 — Tight Coupling: Server Knows Pipeline Internals

**File:** `server.py:30-34`, `server.py:88-106`
**Severity:** High
**Category:** Coupling

**Description:** `LatebraServer.__init__` directly instantiates `SmartScrapePipeline` with the same constructor signature. If the pipeline adds a new parameter (e.g., `cache_dir`), both `LatebraServer.__init__` AND the global `serve()` function must be updated. Also, `handle_tool` dispatches by string name to pipeline methods — any pipeline rename breaks the server.

**Recommendation:** Inject the pipeline via dependency injection:
```python
class LatebraServer:
    def __init__(self, pipeline: SmartScrapePipeline):
        self.pipeline = pipeline
```

Or define a `PipelineProtocol` for testability.

---

### [HIGH] A3 — MCP Tool Definitions Not Auto-Discovered

**File:** `server.py:37-86`
**Severity:** High
**Category:** MCP Compliance

**Description:** Tool definitions are hardcoded as a list of dicts in `tool_definitions` property. Adding a new tool requires editing the dict, the `handle_tool` if/elif chain, AND the pipeline if new functionality is needed. Three places to touch for one feature.

**Recommendation:** Use decorator-based registration pattern:
```python
class LatebraServer:
    _tools: dict[str, ToolDef] = {}

    @tool(name="latebra_scrape", description="...", input_schema={...})
    async def _handle_scrape(self, url: str) -> dict:
        ...
```

Auto-generate `list_tools()` from the registry.

---

### [HIGH] A4 — Mutable Shared State Across Pipeline Layers

**Files:** `pipeline.py:74`, `pipeline.py:106`
**Severity:** High
**Category:** State Management

**Description:** `self._proxy_rotation_count` is a mutable counter shared across all pipeline methods (`scrape`, `check_anonymity`, `scrape_with_captcha`). Concurrent calls would share and corrupt this counter. The MCP server is async — two simultaneous `latebra_scrape` calls would race on `_proxy_rotation_count`.

**Recommendation:** Make the rotation count per-request scoped:
```python
async def scrape(self, url: str) -> ScrapeResult:
    ctx = ScrapeContext()  # per-request isolated state
    ...
```

Or use `asyncio.Lock` to protect the counter.

---

### [MEDIUM] A5 — Layer Interface Contracts Not Formalized

**Files:** `layers/request.py`, `layers/browser.py`, `layers/extraction.py`
**Severity:** Medium
**Category:** Interface Design

**Description:** Each layer returns a different dataclass (`RequestResult`, `BrowserResult`, `ExtractionResult`) with no shared interface or base class. The pipeline must know the specific shape of each layer's output. Swapping curl_cffi for httpx required checking `hasattr(self._session, "aclose")` — meaning the interface is implicit.

**Recommendation:** Define a `LayerResult` protocol with `status: int`, `content: str`, `error: str | None` that all layer results satisfy. This enables layer pluggability.

---

### [MEDIUM] A6 — Config Management Spans Constructor Chains

**Files:** `server.py:24-34`, `pipeline.py:60-73`, `captcha/solver.py:27-33`
**Severity:** Medium
**Category:** Configuration

**Description:** API keys (`two_captcha_key`, `capsolver_key`) are threaded through 3 levels of constructor chain: `serve()` → `LatebraServer` → `SmartScrapePipeline` → `CaptchaSolver`. Changing how a key is loaded requires touching all 4 locations.

**Recommendation:** Use a centralized config object:
```python
@dataclass
class LatebraConfig:
    proxies: list[str] = field(default_factory=list)
    two_captcha_key: str | None = None
    capsolver_key: str | None = None
    cache_dir: str = "~/.cache/latebra"
    stealth_enabled: bool = True
```

Load from environment variables in one place:
```python
config = LatebraConfig.from_env()
pipeline = SmartScrapePipeline(config)
server = LatebraServer(pipeline)
```

---

### [LOW] A7 — No Circuit Breaker on External Services

**Files:** `captcha/solver.py:34`
**Severity:** Low
**Category:** Resilience

**Description:** `CaptchaSolver.__init__` creates a single `httpx.AsyncClient(timeout=60)` shared for all CAPTCHA calls. If 2captcha or capsolver is down, every request will wait up to 5 minutes (60 polls × 5s) before timing out. No circuit breaker prevents cascading failures.

**Recommendation:** Add a circuit breaker to the CAPTCHA solver:
```python
class CaptchaSolver:
    def __init__(self, ..., max_consecutive_failures: int = 3):
        self._failure_count = 0
        self._circuit_open = False
```

---

## Summary

| Severity | Count | Focus |
|----------|-------|-------|
| Critical | 1 | No validation layer (SSRF architecture gap) |
| High | 3 | Tight server-pipeline coupling, hardcoded tool defs, shared mutable state |
| Medium | 2 | No layer interface contracts, config threading |
| Low | 1 | No circuit breaker on external services |

---

## Recommended Actions

1. **Critical:** Add `URLValidator` class at server boundary before any pipeline dispatch
2. **Before release:** Inject pipeline via DI, add decorator-based tool registration, scope proxy counter per-request
3. **Refactor:** Centralize config with `LatebraConfig` dataclass, formalize layer interfaces
