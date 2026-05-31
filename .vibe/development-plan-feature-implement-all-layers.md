# Development Plan: latebra (feature/implement-all-layers branch)

*Generated on 2026-05-30 by Vibe Feature MCP*
*Workflow: [tdd](https://codemcp.github.io/workflows/workflows/tdd)*

## Goal
Implement all 10 latebra components following the SDD spec using TDD (tests first, then implementation).
Async-first, Python 3.12+, maximum anonymity.

## Key Decisions
1. **Layer extraction**: Existing `pipeline.py` has inline curl_cffi/browser logic. After implementing new layer modules, pipeline.py will be refactored to import and delegate to them.
2. **Shared types**: Create `layers/__init__.py` with common exceptions (BlockedError, CaptchaDetectedError) and `layers/types.py` for shared types.
3. **Async-first**: All I/O operations are async per project constraint.
4. **Test isolation**: Tests mock all external services (no real HTTP calls, no real browsers).
5. **Proxy strategy**: In-memory proxy list with circuit breaker (N failures → temporary ban).
6. **Cache**: SQLite with TTL for extraction cache (avoid re-scraping same URL within TTL).
7. **Pipeline refactor**: SmartScrapePipeline imports and uses new layer modules rather than inline logic.
8. **Config model**: Use pydantic.BaseModel for component configs (FingerprintConfig, BrowserConfig, etc.).
9. **Implementation order**: proxy/manager.py → stealth/* → captcha/solver.py → layers/* → pipeline.py refactor → server.py → tests → docs.
10. **Dependency updates**: pyproject.toml needs patchright, nodriver, aiofiles, and lxml added.

## Notes
- Current codebase has pipeline.py with SmartScrapePipeline + inline curl_cffi and browser logic
- ScrapeResult dataclass is correctly defined and should be shared across layer modules
- Existing tests (test_pipeline.py, test_server.py) must continue to pass
- `layers/`, `proxy/`, `stealth/`, `captcha/` directories need to be created under `src/latebra/`
- Component dependency graph: proxy ← request ← pipeline → extraction; stealth ← browser ← pipeline; captcha ← pipeline

## Explore
### Tasks
- [x] Read SDD.md - comprehensive spec for all 8 components
- [x] Read existing pipeline.py - inline curl_cffi/browser logic to be extracted
- [x] Read existing server.py - MCP tool definitions already correct
- [x] Read existing tests - basic test structure, need expansion
- [x] Read pyproject.toml - need to add patchright, nodriver, aiofiles, lxml deps
- [x] Mapped component dependency graph
- [x] Established implementation order

### Completed
- [x] Created development plan file
- [x] Read all existing source files
- [x] Read all existing test files
- [x] Read SDD spec document
- [x] Read pyproject.toml
- [x] Mapped dependencies between components
- [x] Established architecture decisions

## Red
### Tasks
- [ ] *To be added when this phase becomes active*

### Completed
*None yet*

## Green
### Tasks
- [ ] *To be added when this phase becomes active*

### Completed
*None yet*

## Refactor
### Tasks
- [ ] *To be added when this phase becomes active*

### Completed
*None yet*



---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*
