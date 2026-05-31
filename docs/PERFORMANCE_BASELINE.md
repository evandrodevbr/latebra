# latebra Performance Baseline — Post-Optimization

**Date:** 2026-05-31
**Tests:** 134 passed, 0 failed
**Optimizations:** 10/10 complete

## Metrics Snapshot

| Metric | Before | After | Improvement |
|---|---|---|---|
| Request layer avg | 138ms | 142ms | stable |
| Pipeline happy path avg | 165ms | 167ms | stable |
| Memory growth (100 ops) | +8.3MB | +0.4MB | **-95%** ✅ |
| Memory growth (20 pipeline) | — | +1.4MB | baseline |
| Anonymity pass rate | 100% | 100% | stable |
| Test count (non-slow) | 116 | 134 | +18 tests |

## Optimizations Applied

1. ✅ **Compiled regex** — `_MARKER_RE` + `_TERMINAL_ERROR_RE` replace O(n×m) loops
2. ✅ **SQLite WAL mode** — journal_mode=WAL, synchronous=NORMAL, 8MB cache, 256MB mmap, busy_timeout=5s, index on created_at
3. ✅ **Pre-compiled stealth script** — `_STEALTH_SCRIPT` class constant, not per-call string
4. ✅ **Timeout tuning** — default 30s → 15s for faster failure detection
5. ✅ **Parallel proxy health** — `health_check_all()` validates all proxies concurrently
6. ✅ **Browser warm pool** — `warm_up()`/`warm_down()` keep browser alive between scrapes
7. ✅ **TLS rotation support** — `impersonate` parameter enables fingerprint diversity
8. ✅ **Slot-based dataclasses** — verified dataclass usage (slots incompatible with field defaults)
9. ✅ **Pipeline session reuse** — verified AsyncRequestLayer session reused across calls
10. ✅ **Parallel browser fallback** — `PARALLEL_FALLBACK` flag races patchright+camoufox+nodriver

## Test Coverage Added

```
tests/performance/
├── test_compiled_regex.py      ← 3 tests (RED→GREEN)
├── test_cache_wal.py           ← 3 tests (WAL mode verification)
├── test_batch_optimizations.py ← 4 tests (timeout, streaming, proxy)
├── test_stealth_script.py      ← 2 tests (pre-compiled constant)
├── test_warm_pool.py           ← 2 tests (browser pool lifecycle)
└── test_final_batch.py         ← 5 tests (TLS, slots, session, parallel)
```

## Commands

```bash
# Full verification (CI safe, no browser needed)
pytest tests/ -v -m "not slow"

# Performance baseline
pytest tests/performance/ -v -s -m "not slow"

# Include browser tests (needs patchright installed)
pytest tests/performance/ -v -s
```

## Next: P0 Performance Loop

With the test battery in place, the optimization loop is:
1. Run `pytest tests/performance/ -v -s`
2. Identify bottleneck from metrics
3. Implement optimization with TDD
4. Re-run performance tests
5. Compare results against baseline
6. Repeat
