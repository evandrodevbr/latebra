# Search Backend Auto-Detection & Built-in Fallback

**Date:** 2026-06-02
**Author:** Evandro Fonseca Junior
**Status:** Approved

## Goal

Allow latebra to function without SearXNG by providing built-in search engines (Google, DuckDuckGo, Bing) with automatic detection and fallback.

## Requirements

### R1: Configuration
- New env var: `LATEBRA_SEARCH_BACKEND` (values: `auto`, `searxng`, `built-in`, default: `auto`)
- New config field in `LatebraConfig.search_backend`

### R2: Auto Detection
- When `search_backend=auto`, check SearXNG availability via HTTP health check
- If SearXNG responds within 2s, use it
- If not, fallback to built-in engines with warning log

### R3: Built-in Engines
- **Google**: HTML scraping via `httpx`, parse result links/titles/snippets
- **DuckDuckGo**: JSON API via `lite.duckduckgo.com`
- **Bing**: HTML scraping via `httpx`, parse result links/titles/snippets

### R4: Result Format
- All engines return `list[dict]` with keys: `title`, `url`, `snippet`, `engine`
- Same format as SearXNG results for backward compatibility

### R5: Merge Strategy
- Round-robin merge across engines (like SearXNG)
- Deduplication by URL
- Respect `max_results` limit

### R6: Error Handling
- Individual engine failures don't break the search
- Log warnings for failed engines
- Return empty list if all engines fail

### R7: Rate Limiting
- Built-in engines have implicit rate limits
- Use asyncio.Semaphore to limit concurrent requests
- Default: 3 concurrent requests max

## Architecture

```
SearchLayer (modified)
├── _detect_searxng() → bool
├── _search_searxng() → list[dict]
└── _search_builtin() → list[dict]
    ├── GoogleEngine.search()
    ├── DuckDuckGoEngine.search()
    └── BingEngine.search()

BaseSearchEngine (abstract)
├── search(query, max_results) → list[dict]
└── _parse_results(html/json) → list[dict]

GoogleEngine(BaseSearchEngine)
DuckDuckGoEngine(BaseSearchEngine)
BingEngine(BaseSearchEngine)
```

## Files

| File | Action | Purpose |
|------|--------|---------|
| `src/latebra/layers/search.py` | Modify | Add auto-detection, fallback logic |
| `src/latebra/layers/search_builtin.py` | Create | Built-in search engines |
| `src/latebra/config.py` | Modify | Add `search_backend` config |
| `tests/test_layers_search.py` | Create | Unit tests for search layer |
| `tests/test_search_builtin.py` | Create | Unit tests for built-in engines |

## Testing

- TDD: Write failing tests first
- Mock HTTP responses for unit tests
- Integration tests with real engines (marked `@pytest.mark.slow`)
- Test all failure modes (timeout, rate limit, invalid response)
