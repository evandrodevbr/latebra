# Code Quality Audit Report — latebra v0.2.0

**Date:** 2026-05-30
**Auditor:** Hermes Agent (direct review)
**Scope:** All 15 source files in `src/latebra/`
**Framework:** PEP 8, DRY, SOLID, typing best practices

---

## Executive Summary

The codebase is **clean and well-organized** but has significant **code duplication** (DRY violations) in the pipeline orchestrator and across layers. 15 findings: **0 Critical, 5 High, 6 Medium, 4 Low**.

---

## Findings

### [HIGH] Q1 — Massive Code Duplication in `pipeline.py` ScrapeResult Construction

**File:** `src/latebra/pipeline.py`, lines 86-102, 110-123, 126-140, 143-158
**Severity:** High
**Category:** DRY

**Description:** Four nearly identical blocks construct `ScrapeResult` objects with only `layer_used` and `content` varying. Each block is 10+ lines with identical extraction logic.

**Impact:** Every change to result formatting requires editing 4 locations. Tests must cover 4 near-identical paths. Bug risk: inconsistent field initialization (note `error` is set in block 1 but omitted in block 2).

**Fix:** Extract a `_build_success_result(url, content, layer_used, start_time)` helper method.

```python
def _build_success_result(self, url: str, content: str, layer: str, start: float) -> ScrapeResult:
    result = ScrapeResult(
        url=url,
        status="success",
        content=content,
        content_length=len(content),
        layer_used=layer,
        timing_ms=(time.monotonic() - start) * 1000,
        proxies_rotated=self._proxy_rotation_count,
    )
    extr = await self.extraction_layer.extract(content, url)
    result.title = extr.title
    result.extracted_text = extr.text
    result.cached = extr.cached
    return result
```

---

### [HIGH] Q2 — Duplicated Constants Across Modules

**Files:**
- `src/latebra/stealth/fingerprint.py:33-44` (USER_AGENTS)
- `src/latebra/layers/browser.py:52-60` (USER_AGENTS)

**Severity:** High
**Category:** DRY

**Description:** User-Agent strings, viewport dimensions, timezones, and locales are duplicated between `FingerprintGenerator` and `AsyncBrowserLayer`. Adding a new browser version requires editing 2+ files.

**Fix:** Create `src/latebra/constants.py` with all shared constants, or use the existing `FingerprintGenerator` class from `browser.py`.

---

### [HIGH] Q3 — Untyped Public API Returns

**Files:**
- `src/latebra/server.py:125` — `list_tools() -> list` (missing generic parameter)
- `src/latebra/pipeline.py:42` — `to_dict(self) -> dict` (missing generic parameter)
- `src/latebra/pipeline.py:198` — `check_anonymity(self, url: str) -> dict`

**Severity:** High
**Category:** Type Safety

**Description:** Public API methods return bare `list` and `dict` without type parameters. Mypy with `--strict` will flag these. Callers have zero type information on return value structure.

**Fix:**
```python
async def list_tools() -> list[dict[str, Any]]:
    ...

def to_dict(self) -> dict[str, str | int | bool | float]:
    ...

async def check_anonymity(self, url: str) -> dict[str, bool | str | int | float]:
    ...
```

---

### [HIGH] Q4 — Magic Numbers Without Named Constants

**Files:** Multiple

**Severity:** High
**Category:** Readability

**Description:** Critical thresholds are hardcoded without explanation:
- `pipeline.py:86` — `len(req_result.content) > 500` (why 500?)
- `pipeline.py:112` — `result.content[:500]` (why 500 character preview?)
- `captcha/solver.py:84` — `for _ in range(60)` (60 polls × 5s = 5 min, not obvious)
- `captcha/solver.py:85` — `await asyncio.sleep(5)` (poll interval)
- `captcha/solver.py:138` — `for _ in range(60)` (60 polls × 3s = 3 min)
- `request.py:38` — `timeout: int = 30` (should this be float for millisecond precision?)

**Fix:** Define module-level constants:
```python
MIN_CONTENT_LENGTH = 500
PREVIEW_MAX_LENGTH = 500
CAPTCHA_POLL_MAX_ATTEMPTS = 60
CAPTCHA_POLL_INTERVAL_2CAPTCHA = 5
CAPTCHA_POLL_INTERVAL_CAPSOLVER = 3
DEFAULT_REQUEST_TIMEOUT = 30.0
```

---

### [HIGH] Q5 — Silently Swallowed Exceptions in BehaviorSimulator

**File:** `src/latebra/stealth/behavior.py:80,97,109`
**Severity:** High
**Category:** Error Handling

**Description:** All simulation methods catch `except Exception as e` and only log at `debug` level. If mouse/scroll/typing simulation fails, the caller never knows. This silently degrades stealth without any warning.

**Fix:** Either re-raise after logging, or return a boolean success indicator. At minimum, log at `warning` level:
```python
except Exception as e:
    logger.warning("Mouse simulation failed: %s", e)
    raise  # or: return False
```

---

### [MEDIUM] Q6 — `_impersonation_mode` Attribute Set Conditionally

**File:** `src/latebra/layers/request.py:65`
**Severity:** Medium
**Category:** Type Safety

**Description:** `self._impersonation_mode` is only set in the `except ImportError` fallback path (line 65). It's never defined in `__init__` and never set in the normal curl_cffi path. Accessing it when curl_cffi is available will raise `AttributeError`.

**Fix:** Initialize in `__init__`:
```python
self._impersonation_mode: str | None = None
```

---

### [MEDIUM] Q7 — Unused Instance Variable

**File:** `src/latebra/layers/browser.py:41`
**Severity:** Medium
**Category:** Code Cleanliness

**Description:** `self._engine = None` is set in `__init__` but never read or written elsewhere in the class. Dead code.

**Fix:** Remove it.

---

### [MEDIUM] Q8 — `datetime.utcnow()` Deprecated

**File:** `src/latebra/proxy/manager.py:29,37,40`
**Severity:** Medium
**Category:** Deprecation

**Description:** `datetime.utcnow()` is deprecated since Python 3.12. Should use `datetime.now(timezone.utc)`.

**Fix:**
```python
from datetime import datetime, timezone
return datetime.now(timezone.utc) < self.banned_until
```

---

### [MEDIUM] Q9 — Inconsistent URL Construction for CAPTCHA Token

**File:** `src/latebra/pipeline.py:246`
**Severity:** Medium
**Category:** Bug Risk

**Description:** CAPTCHA token appended with `f"{url}?g-recaptcha-response=..."` — if the URL already has query parameters, this produces an invalid URL with double `?`.

**Fix:**
```python
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
parsed = urlparse(url)
params = parse_qs(parsed.query)
params["g-recaptcha-response"] = [captcha.token]
new_query = urlencode(params, doseq=True)
new_url = urlunparse(parsed._replace(query=new_query))
```

---

### [MEDIUM] Q10 — if/elif Chain for Tool Dispatch

**File:** `src/latebra/server.py:88-106`
**Severity:** Medium
**Category:** Extensibility

**Description:** `handle_tool` uses a 3-branch if/elif/else chain. Adding a new tool requires editing this method. A dispatch dict would be cleaner and faster.

**Fix:**
```python
HANDLERS: dict[str, callable] = {
    "latebra_scrape": self._handle_scrape,
    "latebra_scrape_with_browser": self._handle_scrape_with_browser,
    "latebra_check_anonymity": self._handle_check_anonymity,
}
handler = self.HANDLERS.get(name)
if handler is None:
    raise ValueError(f"Unknown tool: {name}")
return await handler(arguments)
```

---

### [MEDIUM] Q11 — Inconsistent Timing Measurement

**Files:** Multiple
**Severity:** Medium
**Category:** Consistency

**Description:** Three different timing APIs are used across the codebase:
- `asyncio.get_event_loop().time()` — `request.py:70`, `captcha/solver.py:44`
- `time.monotonic()` — `pipeline.py:81`
- `datetime.now(timezone.utc)` — `extraction.py:73`

The first two are wall-clock but `time.monotonic()` is preferred for duration measurement. `asyncio.get_event_loop().time()` may drift.

**Fix:** Standardize on `time.monotonic()` for all duration measurements.

---

### [LOW] Q12 — Thread-local SQLite Without Connection Cleanup

**File:** `src/latebra/layers/extraction.py:44-57`
**Severity:** Low
**Category:** Resource Management

**Description:** `ContentCache` creates thread-local SQLite connections but never closes them (`__del__` or context manager). In long-running MCP servers with thread pools, this leaks file descriptors.

**Fix:** Add `close()` method and call it from pipeline's cleanup.

---

### [LOW] Q13 — `md` Tag in Jinja Template but No Templates Used

**File:** None (codebase observation)
**Severity:** Low
**Category:** Dead Code Potential

**Description:** `pyproject.toml` lists `jinja2` as a dependency but no template rendering was found in the codebase. Either unused dep or planned future feature.

---

### [LOW] Q14 — Missing `__all__` in `__init__.py` Files

**Files:** `src/latebra/stealth/__init__.py`, `src/latebra/layers/__init__.py`, `src/latebra/captcha/__init__.py`
**Severity:** Low
**Category:** API Design

**Description:** Package `__init__.py` files are empty. Without `__all__`, `from latebra.stealth import *` imports nothing, and the public API is undefined.

**Fix:** Export key classes in each `__init__.py`:
```python
from latebra.stealth.fingerprint import FingerprintGenerator, BrowserFingerprint
from latebra.stealth.behavior import BehaviorSimulator
__all__ = ["FingerprintGenerator", "BrowserFingerprint", "BehaviorSimulator"]
```

---

### [LOW] Q15 — `json.dumps` in f-string Without `default`

**File:** `src/latebra/stealth/fingerprint.py:123`
**Severity:** Low
**Category:** Reliability

**Description:** `json.dumps(fp.languages)` inside an f-string — if languages ever contains non-string elements, this would raise `TypeError` at runtime silently embedded in generated JS.

**Fix:** Add `default=str` fallback: `json.dumps(fp.languages, default=str)`

---

## Summary

| Severity | Count | Focus Area |
|----------|-------|------------|
| Critical | 0 | — |
| High | 5 | DRY (pipeline duplication), duplicated constants, untyped APIs, magic numbers, silent exceptions |
| Medium | 6 | Conditional attribute, unused var, deprecated utcnow, URL construction bug, if/elif chain, timing inconsistency |
| Low | 4 | Thread-local cleanup, unused dep, missing __all__, json.dumps safety |

---

## Recommended Actions

1. **Immediate (High):** Extract `_build_success_result()` helper in pipeline.py, add type annotations to public API returns, define named constants
2. **Before release (Medium):** Fix `datetime.utcnow()` deprecation, fix CAPTCHA URL construction, add dispatch dict in server.py
3. **Cleanup (Low):** Add `__all__` to packages, add connection cleanup to ContentCache, remove unused `_engine` attribute
