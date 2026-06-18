# Search Backend Auto-Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add built-in search engines (Google, DuckDuckGo, Bing) with auto-detection and fallback when SearXNG is not available.

**Architecture:** Modified SearchLayer with backend detection + new BaseSearchEngine abstract class with 3 concrete implementations.

**Tech Stack:** Python 3.12+, httpx, pytest, asyncio

---

## File Structure

```
src/latebra/
├── layers/
│   ├── search.py              # Modified: add auto-detection
│   └── search_builtin.py      # NEW: built-in engines
├── config.py                  # Modified: add search_backend
tests/
├── test_layers_search.py      # NEW: search layer tests
└── test_search_builtin.py     # NEW: built-in engine tests
```

---

### Task 1: Add search_backend config

**Files:**
- Modify: `src/latebra/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py - add to existing file
def test_latebra_config_search_backend_default():
    """Config should have search_backend default to 'auto'."""
    from latebra.config import LatebraConfig
    config = LatebraConfig()
    assert config.search_backend == "auto"

def test_latebra_config_search_backend_from_env(monkeypatch):
    """Config should read search_backend from env."""
    from latebra.config import LatebraConfig
    monkeypatch.setenv("LATEBRA_SEARCH_BACKEND", "built-in")
    config = LatebraConfig.from_env()
    assert config.search_backend == "built-in"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_config.py::test_latebra_config_search_backend_default -v`
Expected: FAIL with `AttributeError: 'LatebraConfig' object has no attribute 'search_backend'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/config.py - add to LatebraConfig dataclass
search_backend: str = "auto"  # "auto", "searxng", "built-in"

# Add to from_env() method
search_backend=os.environ.get("LATEBRA_SEARCH_BACKEND", "auto"),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_config.py::test_latebra_config_search_backend_default tests/test_config.py::test_latebra_config_search_backend_from_env -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/config.py tests/test_config.py
git commit -m "feat(config): add search_backend configuration option"
```

---

### Task 2: Create BaseSearchEngine abstract class

**Files:**
- Create: `src/latebra/layers/search_builtin.py`
- Test: `tests/test_search_builtin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_builtin.py
import pytest

def test_base_search_engine_import():
    """BaseSearchEngine should be importable."""
    from latebra.layers.search_builtin import BaseSearchEngine
    assert BaseSearchEngine is not None

def test_base_search_engine_has_search_method():
    """BaseSearchEngine should define search method."""
    from latebra.layers.search_builtin import BaseSearchEngine
    assert hasattr(BaseSearchEngine, "search")

def test_base_search_engine_is_abstract():
    """BaseSearchEngine should not be instantiable directly."""
    from latebra.layers.search_builtin import BaseSearchEngine
    with pytest.raises(TypeError):
        BaseSearchEngine()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py -v`
Expected: FAIL with `ImportError: cannot import name 'BaseSearchEngine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/layers/search_builtin.py
"""Built-in search engines for latebra."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseSearchEngine(ABC):
    """Abstract base class for search engines."""

    @abstractmethod
    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Execute search and return results."""
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/layers/search_builtin.py tests/test_search_builtin.py
git commit -m "feat(search): add BaseSearchEngine abstract class"
```

---

### Task 3: Implement DuckDuckGo engine

**Files:**
- Modify: `src/latebra/layers/search_builtin.py`
- Test: `tests/test_search_builtin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_builtin.py - add tests

@pytest.mark.asyncio
async def test_duckduckgo_engine_import():
    """DuckDuckGoEngine should be importable."""
    from latebra.layers.search_builtin import DuckDuckGoEngine
    assert DuckDuckGoEngine is not None

@pytest.mark.asyncio
async def test_duckduckgo_engine_returns_results():
    """DuckDuckGo should return search results."""
    from latebra.layers.search_builtin import DuckDuckGoEngine
    
    engine = DuckDuckGoEngine()
    results = await engine.search("python programming", max_results=3)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3
    
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert r["engine"] == "duckduckgo"

@pytest.mark.asyncio
async def test_duckduckgo_engine_handles_error():
    """DuckDuckGo should handle network errors gracefully."""
    from latebra.layers.search_builtin import DuckDuckGoEngine
    
    engine = DuckDuckGoEngine()
    # Use invalid URL to trigger error
    engine._api_url = "http://localhost:9999"
    results = await engine.search("test", max_results=3)
    
    assert isinstance(results, list)
    assert len(results) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_duckduckgo_engine_returns_results -v`
Expected: FAIL with `ImportError: cannot import name 'DuckDuckGoEngine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/layers/search_builtin.py - add to file

import httpx


class DuckDuckGoEngine(BaseSearchEngine):
    """DuckDuckGo search via lite API."""

    def __init__(self, timeout: int = 10) -> None:
        self._api_url = "https://lite.duckduckgo.com/lite/"
        self._timeout = timeout

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search DuckDuckGo and return results."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._api_url,
                    data={"q": query},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.raise_for_status()
                return self._parse_results(resp.text)[:max_results]
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            return []

    def _parse_results(self, html: str) -> list[dict[str, Any]]:
        """Parse DuckDuckGo lite HTML response."""
        import re
        
        results = []
        # Find result links
        link_pattern = re.compile(
            r'<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        )
        snippet_pattern = re.compile(
            r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', re.DOTALL
        )
        
        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)
        
        for i, (url, title) in enumerate(links[:len(snippets)]):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            results.append({
                "title": title.strip(),
                "url": url,
                "snippet": snippet,
                "engine": "duckduckgo",
            })
        
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_duckduckgo_engine_returns_results tests/test_search_builtin.py::test_duckduckgo_engine_handles_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/layers/search_builtin.py tests/test_search_builtin.py
git commit -m "feat(search): add DuckDuckGo built-in engine"
```

---

### Task 4: Implement Google engine

**Files:**
- Modify: `src/latebra/layers/search_builtin.py`
- Test: `tests/test_search_builtin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_builtin.py - add tests

@pytest.mark.asyncio
async def test_google_engine_returns_results():
    """Google should return search results."""
    from latebra.layers.search_builtin import GoogleEngine
    
    engine = GoogleEngine()
    results = await engine.search("python programming", max_results=3)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3
    
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert r["engine"] == "google"

@pytest.mark.asyncio
async def test_google_engine_handles_rate_limit():
    """Google should handle rate limits gracefully."""
    from latebra.layers.search_builtin import GoogleEngine
    
    engine = GoogleEngine()
    # Multiple rapid requests
    for _ in range(5):
        results = await engine.search("test", max_results=1)
        assert isinstance(results, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_google_engine_returns_results -v`
Expected: FAIL with `ImportError: cannot import name 'GoogleEngine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/layers/search_builtin.py - add to file

class GoogleEngine(BaseSearchEngine):
    """Google search via HTML scraping."""

    def __init__(self, timeout: int = 10) -> None:
        self._search_url = "https://www.google.com/search"
        self._timeout = timeout
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search Google and return results."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    self._search_url,
                    params={"q": query, "num": max_results},
                    headers=self._headers,
                )
                resp.raise_for_status()
                return self._parse_results(resp.text)[:max_results]
        except Exception as e:
            logger.warning("Google search failed: %s", e)
            return []

    def _parse_results(self, html: str) -> list[dict[str, Any]]:
        """Parse Google HTML response."""
        import re
        
        results = []
        # Find result blocks
        block_pattern = re.compile(
            r'<div[^>]*class="[^"]*"[^>]*>.*?<a[^>]+href="/url\?q=([^&"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?</a>.*?<span[^>]*class="[^"]*"[^>]*>(.*?)</span>',
            re.DOTALL,
        )
        
        matches = block_pattern.findall(html)
        for url, title, snippet in matches[:20]:  # Limit parsing
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
            if title_clean and url.startswith("http"):
                results.append({
                    "title": title_clean,
                    "url": url,
                    "snippet": snippet_clean,
                    "engine": "google",
                })
        
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_google_engine_returns_results -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/layers/search_builtin.py tests/test_search_builtin.py
git commit -m "feat(search): add Google built-in engine"
```

---

### Task 5: Implement Bing engine

**Files:**
- Modify: `src/latebra/layers/search_builtin.py`
- Test: `tests/test_search_builtin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_builtin.py - add tests

@pytest.mark.asyncio
async def test_bing_engine_returns_results():
    """Bing should return search results."""
    from latebra.layers.search_builtin import BingEngine
    
    engine = BingEngine()
    results = await engine.search("python programming", max_results=3)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3
    
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert r["engine"] == "bing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_bing_engine_returns_results -v`
Expected: FAIL with `ImportError: cannot import name 'BingEngine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/layers/search_builtin.py - add to file

class BingEngine(BaseSearchEngine):
    """Bing search via HTML scraping."""

    def __init__(self, timeout: int = 10) -> None:
        self._search_url = "https://www.bing.com/search"
        self._timeout = timeout
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search Bing and return results."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    self._search_url,
                    params={"q": query, "count": max_results},
                    headers=self._headers,
                )
                resp.raise_for_status()
                return self._parse_results(resp.text)[:max_results]
        except Exception as e:
            logger.warning("Bing search failed: %s", e)
            return []

    def _parse_results(self, html: str) -> list[dict[str, Any]]:
        """Parse Bing HTML response."""
        import re
        
        results = []
        # Find result blocks
        block_pattern = re.compile(
            r'<li[^>]*class="b_algo"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>',
            re.DOTALL,
        )
        
        matches = block_pattern.findall(html)
        for url, title, snippet in matches[:20]:
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
            if title_clean and url.startswith("http"):
                results.append({
                    "title": title_clean,
                    "url": url,
                    "snippet": snippet_clean,
                    "engine": "bing",
                })
        
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_bing_engine_returns_results -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/layers/search_builtin.py tests/test_search_builtin.py
git commit -m "feat(search): add Bing built-in engine"
```

---

### Task 6: Implement BuiltInSearchLayer with merge

**Files:**
- Modify: `src/latebra/layers/search_builtin.py`
- Test: `tests/test_search_builtin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_builtin.py - add tests

@pytest.mark.asyncio
async def test_builtin_search_layer_exists():
    """BuiltInSearchLayer should be importable."""
    from latebra.layers.search_builtin import BuiltInSearchLayer
    assert BuiltInSearchLayer is not None

@pytest.mark.asyncio
async def test_builtin_search_layer_search():
    """BuiltInSearchLayer should search across multiple engines."""
    from latebra.layers.search_builtin import BuiltInSearchLayer
    
    layer = BuiltInSearchLayer()
    results = await layer.search("python programming", max_results=5)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 5
    
    # Check round-robin merge (different engines)
    engines = {r["engine"] for r in results}
    assert len(engines) > 1, "Should have results from multiple engines"

@pytest.mark.asyncio
async def test_builtin_search_layer_dedup():
    """BuiltInSearchLayer should deduplicate results by URL."""
    from latebra.layers.search_builtin import BuiltInSearchLayer
    
    layer = BuiltInSearchLayer()
    results = await layer.search("python", max_results=10)
    
    urls = [r["url"] for r in results]
    assert len(urls) == len(set(urls)), "Results should be deduplicated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_builtin_search_layer_search -v`
Expected: FAIL with `ImportError: cannot import name 'BuiltInSearchLayer'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/layers/search_builtin.py - add to file

import asyncio


class BuiltInSearchLayer:
    """Search across multiple built-in engines with round-robin merge."""

    def __init__(self, timeout: int = 10, max_concurrent: int = 3) -> None:
        self._engines = [
            DuckDuckGoEngine(timeout=timeout),
            GoogleEngine(timeout=timeout),
            BingEngine(timeout=timeout),
        ]
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def search(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search all engines concurrently and merge results."""
        async def _search_engine(engine: BaseSearchEngine) -> list[dict[str, Any]]:
            async with self._semaphore:
                return await engine.search(query, max_results=max_results)

        # Run all engines concurrently
        tasks = [_search_engine(engine) for engine in self._engines]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [
            r for r in all_results if isinstance(r, list)
        ]

        # Round-robin merge
        merged = []
        seen_urls: set[str] = set()
        max_len = max((len(r) for r in valid_results), default=0)

        for i in range(max_len):
            for engine_results in valid_results:
                if i < len(engine_results):
                    result = engine_results[i]
                    url = result.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        merged.append(result)
                        if len(merged) >= max_results:
                            return merged

        return merged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_builtin_search_layer_search tests/test_search_builtin.py::test_builtin_search_layer_dedup -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/layers/search_builtin.py tests/test_search_builtin.py
git commit -m "feat(search): add BuiltInSearchLayer with round-robin merge"
```

---

### Task 7: Modify SearchLayer for auto-detection

**Files:**
- Modify: `src/latebra/layers/search.py`
- Test: `tests/test_layers_search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_layers_search.py
import pytest

@pytest.mark.asyncio
async def test_search_layer_auto_detects_searxng():
    """SearchLayer should detect SearXNG availability."""
    from latebra.layers.search import SearchLayer
    
    # With running SearXNG
    layer = SearchLayer(base_url="http://localhost:8090", search_backend="auto")
    assert await layer._detect_searxng() is True

@pytest.mark.asyncio
async def test_search_layer_auto_fallback():
    """SearchLayer should fallback to built-in when SearXNG unavailable."""
    from latebra.layers.search import SearchLayer
    
    layer = SearchLayer(base_url="http://localhost:9999", search_backend="auto")
    results = await layer.search("python", max_results=3)
    
    assert isinstance(results, list)
    # Should return results from built-in engines
    assert len(results) > 0

@pytest.mark.asyncio
async def test_search_layer_explicit_builtin():
    """SearchLayer should use built-in when explicitly configured."""
    from latebra.layers.search import SearchLayer
    
    layer = SearchLayer(search_backend="built-in")
    results = await layer.search("python", max_results=3)
    
    assert isinstance(results, list)
    assert len(results) > 0

@pytest.mark.asyncio
async def test_search_layer_explicit_searxng():
    """SearchLayer should use SearXNG when explicitly configured."""
    from latebra.layers.search import SearchLayer
    
    layer = SearchLayer(base_url="http://localhost:8090", search_backend="searxng")
    results = await layer.search("python", max_results=3)
    
    assert isinstance(results, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_layers_search.py -v`
Expected: FAIL with `TypeError: unexpected keyword argument 'search_backend'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/layers/search.py - modify existing file

from latebra.layers.search_builtin import BuiltInSearchLayer

DEFAULT_SEARXNG_URL = "http://localhost:8090"


class SearchLayer:
    """Privacy-preserving web search via SearXNG or built-in engines."""

    def __init__(
        self,
        base_url: str = DEFAULT_SEARXNG_URL,
        timeout: int = 10,
        search_backend: str = "auto",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.search_backend = search_backend
        self._builtin = BuiltInSearchLayer(timeout=timeout)
        self._searxng_available: bool | None = None

    async def _detect_searxng(self) -> bool:
        """Check if SearXNG is available."""
        if self._searxng_available is not None:
            return self._searxng_available
        
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{self.base_url}/search", params={"q": "test", "format": "json"})
                self._searxng_available = resp.status_code == 200
        except Exception:
            self._searxng_available = False
        
        return self._searxng_available

    async def search(
        self,
        query: str,
        max_results: int = 10,
        engines: str | None = None,
        categories: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a web search and return structured results."""
        # Determine backend
        use_searxng = False
        
        if self.search_backend == "auto":
            use_searxng = await self._detect_searxng()
            if not use_searxng:
                logger.warning("SearXNG not available, using built-in engines")
        elif self.search_backend == "searxng":
            use_searxng = True
        # else: use_searxng stays False (built-in)

        if use_searxng:
            return await self._search_searxng(query, max_results, engines, categories)
        else:
            return await self._builtin.search(query, max_results)

    async def _search_searxng(
        self,
        query: str,
        max_results: int,
        engines: str | None,
        categories: str | None,
    ) -> list[dict[str, Any]]:
        """Search using SearXNG."""
        # ... existing SearXNG code ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_layers_search.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/layers/search.py tests/test_layers_search.py
git commit -m "feat(search): add auto-detection and fallback to SearchLayer"
```

---

### Task 8: Update server.py to pass search_backend

**Files:**
- Modify: `src/latebra/server.py`
- Modify: `src/latebra/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_server.py - add test

def test_latebra_server_search_backend():
    """Server should pass search_backend to SearchLayer."""
    from latebra.server import LatebraServer
    from latebra.config import LatebraConfig
    
    config = LatebraConfig(search_backend="built-in")
    server = LatebraServer(config=config)
    
    assert server.search.search_backend == "built-in"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_server.py::test_latebra_server_search_backend -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'config'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/latebra/server.py - modify LatebraServer.__init__

def __init__(
    self,
    proxies: list[str] | None = None,
    two_captcha_key: str | None = None,
    capsolver_key: str | None = None,
    searxng_url: str = DEFAULT_SEARXNG_URL,
    config: LatebraConfig | None = None,
) -> None:
    self.pipeline = SmartScrapePipeline(
        proxies=proxies,
        two_captcha_key=two_captcha_key,
        capsolver_key=capsolver_key,
    )
    
    # Use config if provided, otherwise defaults
    search_backend = config.search_backend if config else "auto"
    self.search = SearchLayer(
        base_url=searxng_url,
        search_backend=search_backend,
    )
    # ... rest unchanged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_server.py::test_latebra_server_search_backend -v`
Expected: PASS

- [ ] **Step 5: Run all tests**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_server.py tests/test_layers_search.py tests/test_search_builtin.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/latebra/server.py tests/test_server.py
git commit -m "feat(server): pass search_backend config to SearchLayer"
```

---

### Task 9: Integration test with real engines

**Files:**
- Test: `tests/test_search_builtin.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_search_builtin.py - add integration tests

@pytest.mark.slow
@pytest.mark.asyncio
async def test_builtin_search_integration():
    """Integration test: search across all built-in engines."""
    from latebra.layers.search_builtin import BuiltInSearchLayer
    
    layer = BuiltInSearchLayer()
    results = await layer.search("artificial intelligence", max_results=10)
    
    assert len(results) > 0
    print(f"\n  Found {len(results)} results:")
    for i, r in enumerate(results[:5], 1):
        print(f"    {i}. [{r['engine']}] {r['title'][:50]}")
```

- [ ] **Step 2: Run integration test**

Run: `cd /home/evandro/latebra && .venv/bin/pytest tests/test_search_builtin.py::test_builtin_search_integration -v -s`
Expected: PASS with real results

- [ ] **Step 3: Final commit**

```bash
git add tests/test_search_builtin.py
git commit -m "test(search): add integration tests for built-in engines"
```

---

### Task 10: Update AGENTS.md and skill

**Files:**
- Modify: `AGENTS.md`
- Modify: `~/.hermes/skills/software-development/latebra/SKILL.md`

- [ ] **Step 1: Update documentation**

Add to AGENTS.md:
```markdown
## Search Backend Configuration

Latebra supports two search backends:

1. **SearXNG** (default if available) - Self-hosted metasearch engine
2. **Built-in** - Google, DuckDuckGo, Bing via HTML scraping

Configuration via env var:
- `LATEBRA_SEARCH_BACKEND=auto` (default) - Try SearXNG, fallback to built-in
- `LATEBRA_SEARCH_BACKEND=searxng` - Force SearXNG
- `LATEBRA_SEARCH_BACKEND=built-in` - Force built-in engines
```

- [ ] **Step 2: Update skill**

Patch the latebra skill to document the new search backend.

- [ ] **Step 3: Final commit**

```bash
git add AGENTS.md
git commit -m "docs: add search backend configuration documentation"
```
