# Security Audit Report — latebra v0.2.0

**Date:** 2026-05-30  
**Auditor:** Sisyphus (automated code review)  
**Scope:** All 15 source files in `src/latebra/` + 10 test files in `tests/`  
**Framework:** OWASP Top 10:2021  
**Files reviewed:** 26 Python files, pyproject.toml, .gitignore, docs/SDD.md

---

## Executive Summary

latebra is an MCP server designed for web scraping — its core function is making outbound HTTP requests to arbitrary URLs. This design inherently creates a **Server-Side Request Forgery (SSRF)** attack surface. The application lacks all forms of URL validation, allowing an attacker to probe internal networks, access cloud metadata services, and potentially read local files.

**2 Critical, 4 High, 4 Medium, 4 Low** findings.

---

## Findings

### [CRITICAL] C1 — Unrestricted SSRF via All Layers

**OWASP:** A10:2021 — Server-Side Request Forgery (SSRF)  
**File(s):** [`pipeline.py`](file:///home/evandro/latebra/src/latebra/pipeline.py), [`server.py`](file:///home/evandro/latebra/src/latebra/server.py), [`request.py`](file:///home/evandro/latebra/src/latebra/layers/request.py), [`browser.py`](file:///home/evandro/latebra/src/latebra/layers/browser.py)  

**Description:** Every MCP tool (`latebra_scrape`, `latebra_scrape_with_browser`, `latebra_check_anonymity`) accepts a `url` parameter and passes it directly to curl_cffi or a headless browser without **any** validation. No scheme restriction, no host allowlisting, no internal IP blocking.

**Attack scenario:**
```
# AWS metadata exfiltration
latebra_scrape("http://169.254.169.254/latest/meta-data/iam/security-credentials/")

# Internal service probing
latebra_scrape("http://localhost:5432")         # PostgreSQL
latebra_scrape("http://10.0.0.1:6379")          # Redis
latebra_scrape_with_browser("http://192.168.1.1/admin")

# Local file read (browser layer, file:// scheme)
latebra_scrape_with_browser("file:///etc/passwd")
```

**Recommendation:** Add a URL validation layer before any request:
1. Restrict schemes to `http://` and `https://` only
2. Resolve and block private/loopback/link-local IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, ::1, fc00::/7)
3. Consider an allowlist for known-safe hostnames
4. Validate URL format with `urllib.parse` before dispatch

---

### [HIGH] H1 — Missing URL Validation on All MCP Tool Inputs

**OWASP:** A03:2021 — Injection  
**File(s):** [`server.py#L47-L51`](file:///home/evandro/latebra/src/latebra/server.py#L47-L51), [`server.py#L60-L67`](file:///home/evandro/latebra/src/latebra/server.py#L60-L67), [`server.py#L76-L85`](file:///home/evandro/latebra/src/latebra/server.py#L76-L85)  

**Description:** The `inputSchema` for `url` parameters uses only `{"type": "string"}`. No format validation (`format: "uri"`), no `pattern`, no `minLength`/`maxLength`. Strings like `""`, `"not-a-url"`, or extremely long strings are accepted and would cause undefined behavior downstream.

**Code:**
```json
"url": {
    "type": "string",
    "description": "Target URL to scrape",
},
```

**Recommendation:**
```json
"url": {
    "type": "string",
    "format": "uri",
    "minLength": 1,
    "maxLength": 2048,
    "pattern": "^https?://",
    "description": "Target URL to scrape (HTTP/HTTPS only)",
},
```

---

### [HIGH] H2 — Error Messages Leak Internal Details

**OWASP:** A04:2021 — Insecure Design  
**File(s):** [`request.py#L87`](file:///home/evandro/latebra/src/latebra/layers/request.py#L87), [`browser.py#L86`](file:///home/evandro/latebra/src/latebra/layers/browser.py#L86), [`extraction.py#L119-L120`](file:///home/evandro/latebra/src/latebra/layers/extraction.py#L119-L120)  

**Description:** All exceptions are converted to strings and returned to the MCP client via `ScrapeResult.error`. These can leak:

- File paths (ImportError, OSError messages)
- Internal IP addresses / hostnames
- Library versions from stack traces
- Database paths
- TLS certificate details

**Code:**
```python
except Exception as e:
    logger.warning("Request attempt %d failed: %s", attempt + 1, e)
    result.error = str(e)  # <-- raw error leaked to client
```

```python
except Exception as e:
    logger.warning("Crawl4AI extraction failed: %s", e)
    self._extract_fallback(html, url, result, selector)
    # error IS NOT set here, but in request layer it is
```

**Recommendation:** 
- Return generic error messages to clients: `"Request layer failed"`, `"Browser engine unavailable"`
- Log full exception details server-side only
- Audit all `result.error = str(e)` assignments

---

### [HIGH] H3 — Proxy Credentials Logged in Plaintext

**OWASP:** A04:2021 — Insecure Design (Logging of Sensitive Data)  
**File(s):** [`manager.py#L77`](file:///home/evandro/latebra/src/latebra/proxy/manager.py#L77), [`manager.py#L41`](file:///home/evandro/latebra/src/latebra/proxy/manager.py#L41)  

**Description:** The proxy URL, which typically contains credentials in `protocol://user:password@host:port` format, is logged verbatim:

```python
def add_proxy(self, url: str) -> None:
    self._entries.append(ProxyEntry(url=url))
    logger.info("Added proxy: %s", url)  # <-- credentials in logs!
```

```python
logger.info("Proxy %s banned for %ds", self.url, cooldown)  # <-- same issue
```

If the server runs with `--verbose`, all logs go to stderr at DEBUG level. Proxy URLs from `PROXY_LIST` env var flow through here.

**Recommendation:**
1. Parse and redact credentials before logging: `re.sub(r'://[^:]+:[^@]+@', '://***:***@', url)`
2. Store proxy credential components separately: host, port, username, password as distinct fields
3. Use a dedicated sanitized `__repr__` for ProxyEntry logging

---

### [HIGH] H4 — URL Injection in CAPTCHA Token Parameter

**OWASP:** A03:2021 — Injection  
**File(s):** [`pipeline.py#L244-L248`](file:///home/evandro/latebra/src/latebra/pipeline.py#L244-L248)  

**Description:** The reCAPTCHA response token is appended to the URL via string concatenation:

```python
req_result = await self.request_layer.fetch(
    f"{url}?g-recaptcha-response={captcha.token}",
    proxy=proxy,
)
```

This breaks if `url` already contains query parameters (e.g., `?page=1` becomes `?g-recaptcha-response=...` — losing the original parameter). Additionally, the token is not URL-encoded, and there is no hostname validation before the CAPTCHA retry.

**Recommendation:**
```python
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

parsed = urlparse(url)
params = parse_qs(parsed.query)
params["g-recaptcha-response"] = [captcha.token]
new_query = urlencode(params, doseq=True)
new_url = urlunparse(parsed._replace(query=new_query))
```

---

### [MEDIUM] M1 — Path Traversal via Custom Cache DB Path

**OWASP:** A01:2021 — Broken Access Control  
**File(s):** [`extraction.py#L35-L41`](file:///home/evandro/latebra/src/latebra/layers/extraction.py#L35-L41)  

**Description:** The `ContentCache.__init__` accepts a custom `db_path` with no path sanitization:

```python
def __init__(self, db_path: str | None = None):
    if db_path is None:
        db_path = os.path.expanduser("~/.cache/latebra/cache.db")
    dir_path = os.path.dirname(db_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    self.db_path = db_path
```

An attacker using the Python library API could pass `../../etc/malicious.db` to write outside the intended directory. While `ContentCache` is not directly exposed via MCP tools, the library API is public.

**Recommendation:**
```python
import os
# Resolve and validate the path
real_path = os.path.realpath(db_path)
allowed_base = os.path.realpath(os.path.expanduser("~/.cache/latebra"))
if not real_path.startswith(allowed_base):
    raise ValueError(f"db_path must be within {allowed_base}")
```

---

### [MEDIUM] M2 — Fragile JavaScript Injection Pattern

**OWASP:** A03:2021 — Injection  
**File(s):** [`fingerprint.py#L97-L126`](file:///home/evandro/latebra/src/latebra/stealth/fingerprint.py#L97-L126)  

**Description:** The `generate_stealth_init_script()` method uses f-string interpolation to inject values directly into JavaScript code:

```python
return f"""
    ...
    if (param === 37445) return "{fp.webgl_vendor}";
    ...
    Object.defineProperty(navigator, 'platform', {{ get: () => '{fp.platform}' }});
"""
```

Currently safe because values come from hardcoded class-level lists. However:
- The pattern would become an **XSS vector** if any value ever comes from external input
- The `json.dumps()` call on `languages` is correct, but the other values use raw f-string injection
- A platform string containing `'` would break the JavaScript syntax

**Recommendation:** Use `json.dumps()` for ALL interpolated values, not just `languages`:
```python
Object.defineProperty(navigator, 'platform', {{ get: () => {json.dumps(fp.platform)} }});
```

---

### [MEDIUM] M3 — No Rate Limiting on MCP Tools

**OWASP:** A04:2021 — Insecure Design  
**File(s):** [`server.py`](file:///home/evandro/latebra/src/latebra/server.py)  

**Description:** There is no rate limiting, concurrency control, or request throttling on any MCP tool. An attacker (or buggy MCP client) could:
- Launch thousands of concurrent scrape requests
- Exhaust proxy pool
- Trigger CAPTCHA solving costs (costly API calls)
- Overwhelm the SQLite cache (write amplification)

**Recommendation:**
- Add `asyncio.Semaphore` to limit concurrent in-flight requests
- Implement per-tool cooldown periods
- Set a maximum total concurrent pipeline execution count (e.g., 5)

---

### [MEDIUM] M4 — Lack of Dependency Vulnerability Scanning

**OWASP:** A06:2021 — Vulnerable and Outdated Components  
**File(s):** [`pyproject.toml`](file:///home/evandro/latebra/pyproject.toml)  

**Description:** 
- All dependencies use `>=` (minimum-only) version constraints — no upper bounds, no lockfile committed
- No dependency audit tool configured (`pip-audit`, `safety`, `bandit`)
- No CI/CD security scanning

**Recommendation:**
1. Add `pip-audit` to dev dependencies and CI
2. Commit a lockfile (`requirements.txt` or `uv.lock`)
3. Add upper-bound constraints for major version safety
4. Run `bandit` as a pre-commit hook for static analysis

---

### [LOW] L1 — SQLite Cache Content Not Encrypted at Rest

**OWASP:** A02:2021 — Cryptographic Failures  
**File(s):** [`extraction.py#L35-L41`](file:///home/evandro/latebra/src/latebra/layers/extraction.py#L35-L41)  

**Description:** The SQLite cache at `~/.cache/latebra/cache.db` stores scraped content unencrypted. If scraping authenticated pages (e.g., behind login), sensitive user data could persist on disk with no protection. The file permissions depend on the system umask.

**Recommendation:** Document this in a security section of the README. Consider encrypting sensitive fields or using file-level permissions (`os.chmod` to `0o600`).

---

### [LOW] L2 — Inconsistent Repository URL in pyproject.toml

**OWASP:** N/A (integrity)  
**File(s):** [`pyproject.toml#L38-L39`](file:///home/evandro/latebra/pyproject.toml#L38-L39)  

**Description:** `homepage` and `repository` URLs point to `https://github.com/evandrofjs/latebra`, but the README uses `https://github.com/evandrodevbr/latebra`. This inconsistency could lead users to a wrong/abandoned repository.

**Recommendation:** Update `pyproject.toml` URLs to match the canonical `evandrodevbr` username.

---

### [LOW] L3 — ReDoS Risk in Link Extraction Regex

**OWASP:** A03:2021 — Injection  
**File(s):** [`extraction.py#L190`](file:///home/evandro/latebra/src/latebra/layers/extraction.py#L190)  

**Description:** The fallback link extractor uses:
```python
re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
```

On extremely large HTML documents (10MB+), the negated character class `[^"\']+` combined with `findall` could cause performance issues. Not a true ReDoS (no nested quantifiers), but could cause CPU exhaustion on malicious input.

**Recommendation:** Add a timeout or HTML size limit before running regex extraction. Consider using an HTML parser (already imported `HTMLParser`) for link extraction as well.

---

### [LOW] L4 — User-Agent Header Static in Fallback httpx Session

**OWASP:** A05:2021 — Security Misconfiguration  
**File(s):** [`request.py#L54-L64`](file:///home/evandro/latebra/src/latebra/layers/request.py#L54-L64)  

**Description:** When curl_cffi is unavailable, the httpx fallback uses a hardcoded User-Agent string. While this is not a security vulnerability per se, it creates a detectable fingerprint that anti-bot systems can block — defeating the purpose of the anonymity pipeline.

**Recommendation:** Rotate the fallback User-Agent using the same random selection pattern as the browser layer.

---

## Positive Findings (Things Done Well)

1. ✅ **Parameterized SQL queries** used in all SQLite operations — no SQL injection vector
2. ✅ **`.env` in `.gitignore`** — environment secrets excluded from version control
3. ✅ **No hardcoded credentials** in source code — API keys are constructor parameters
4. ✅ **No `subprocess` calls** — no command injection surface
5. ✅ **Thread-local SQLite connections** — correct thread safety pattern for sqlite3
6. ✅ **Content hash keys** (SHA-256) used for cache keys instead of raw URLs
7. ✅ **Circuit breaker pattern** for proxy banning — prevents endless retries on bad proxies
8. ✅ **No `eval()`, `exec()`, `pickle` deserialization** — no code execution vectors
9. ✅ **Test coverage** for core components including error paths

---

## Summary

| Severity | Count | Key Finding |
|----------|-------|-------------|
| Critical | 1 | Unrestricted SSRF — all layers accept arbitrary URLs |
| High     | 4 | Missing URL validation, error leakage, credential logging, URL injection |
| Medium   | 4 | Path traversal, fragile JS injection, no rate limiting, no dep scanning |
| Low      | 4 | Unencrypted cache, repo URL mismatch, ReDoS risk, static UA fingerprint |

**Overall risk: HIGH.** The SSRF vulnerability alone is a critical finding given the application's purpose (web scraping). All High findings should be addressed before production deployment. The lack of URL validation is the single most impactful fix needed.

---

## Recommended Remediation Priority

1. **Immediate** (Critical): Add SSRF protection — scheme restriction + internal IP blocking
2. **Before release** (High): URL format validation, error message sanitization, credential redaction in logs
3. **Short-term** (Medium): Rate limiting, dependency scanning, path traversal fix
4. **Ongoing** (Low): Cache encryption docs, regex hardening, profile consistency fix
