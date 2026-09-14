# latebra

**MCP server for anti-bot web scraping: a self-hosted, multi-layer evasion pipeline (TLS impersonation, stealth browsers, extraction) exposed as MCP tools for AI agents.**

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.x-green.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-163%20passed%20of%20166-brightgreen.svg)](https://github.com/evandrodevbr/latebra/tree/master/tests)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

## About

Scraping sites protected by anti-bot systems (Cloudflare, DataDome, Akamai and similar) usually means either paying for a cloud scraping API or hand-building a browser stack with stealth patches. latebra packages both paths into one local MCP server: an MCP client (Claude, Cursor, Hermes, any MCP-capable agent) calls tools like `latebra_scrape` or `latebra_search` and the server decides, per request, whether a plain HTTP request with TLS impersonation is enough or a stealth browser is needed.

What it does:

- exposes 8 MCP tools over stdio (scrape, browser scrape, batch scrape, crawl, search, interact, anonymity check, log path);
- climbs an evasion pipeline automatically: `curl_cffi` request with Chrome TLS fingerprint, then Patchright, Camoufox or nodriver browsers;
- extracts and caches content (Crawl4AI when installed, built-in extraction otherwise, SQLite cache with TTL);
- searches the web through a local SearXNG instance when available, falling back to DuckDuckGo, Google and Bing through the `ddgs` library;
- supports optional proxy rotation with a circuit breaker, behavioral simulation and CAPTCHA solving via 2Captcha/Capsolver.

Everything runs locally. There is no cloud dependency and no account required.

## How it works

```
MCP client (JSON-RPC over stdio)
        |
        v
server.py            LatebraServer, 8 tools, dispatch by tool name
        |
        v
SmartScrapePipeline  per-URL decision, falls back layer by layer
        |
        +-- Layer 1: AsyncRequestLayer (curl_cffi, Chrome impersonation)
        |       success -> extraction + SQLite cache
        |       failure -> terminal network error? stop : Layer 2
        |
        +-- Layer 2: AsyncBrowserLayer (Patchright -> Camoufox -> nodriver)
        |       success -> extraction
        |
        +-- Layer 3: AsyncExtractionLayer (Cache -> Crawl4AI -> built-in)
        |
        +-- Helpers: ProxyManager (rotation + circuit breaker),
                     stealth fingerprint/behavior, CaptchaSolver
```

Search has its own two-step path: `SearchLayer` probes SearXNG at `http://localhost:8090`; if it answers, the query goes there, otherwise it falls back to the built-in engines (`BuiltInSearchLayer` over `ddgs`). The `LATEBRA_SEARCH_BACKEND` environment variable forces `auto` (default), `searxng` or `built-in`.

## Stack

| Layer | Choice |
|---|---|
| Runtime | Python 3.12+, async throughout |
| MCP | `mcp` SDK 1.x (stdio server) |
| HTTP / TLS | `curl_cffi` with Chrome impersonation profiles |
| Browsers (optional) | Patchright, Camoufox, nodriver |
| Extraction (optional) | Crawl4AI, plus built-in regex/HTML extraction |
| Search | SearXNG (optional) or `ddgs` (DuckDuckGo, Google, Bing) |
| Cache | SQLite with TTL (`~/.cache/latebra`) |
| Tests / tooling | pytest, pytest-asyncio, ruff, mypy |
| Packaging | setuptools, `uv` lockfile, console scripts `latebra` and `latebra-mcp` |

## Requirements

- Python 3.12 or newer (verified on 3.12.14)
- `uv` (recommended) or `pip`
- Network access for real scraping
- Optional: Docker (to run SearXNG), proxies, 2Captcha/Capsolver API keys
- For browser mode: Chrome/Chromium installed (nodriver uses it) or the stealth browsers downloaded by `latebra install`

## Quick start

```bash
git clone https://github.com/evandrodevbr/latebra.git
cd latebra

# Virtualenv + install (core + test tools)
uv venv .venv --python 3.12
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Start the MCP server on stdio
python -m latebra run
```

`uvx latebra` does **not** work yet: the package is not published on PyPI. Install from the repository.

For the full install (browser engines + Crawl4AI extraction):

```bash
uv pip install -e ".[all,dev]"
latebra install                  # downloads Patchright Chromium and Camoufox binaries
```

The `pip` path works the same way: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[all,dev]"`.

### MCP client configuration

Example for any MCP client that takes a command and arguments (adjust the path to your venv):

```json
{
  "mcpServers": {
    "latebra": {
      "command": "/path/to/latebra/.venv/bin/python",
      "args": ["-m", "latebra", "run"]
    }
  }
}
```

Or use the console script installed by the wheel: `latebra-mcp` (same stdio server).

One-off installers are provided as `install.sh` (Linux/macOS) and `install.ps1` (Windows); both clone `master` into `~/.latebra` (override with `LATEBRA_HOME`), create a venv, install `.[all]` and add the server to the Claude Desktop config when it exists.

## MCP tools

Verified with a real `initialize` + `tools/list` handshake against the packaged wheel; the server reports exactly these 8 tools:

| Tool | What it does | Parameters |
|---|---|---|
| `latebra_scrape` | Runs the multi-layer pipeline for one URL (request first, browser fallback). | `url` (required) |
| `latebra_scrape_with_browser` | Skips the request layer and uses a browser engine directly. | `url` (required), `browser` = `patchright` \| `camoufox` \| `nodriver` (default `patchright`) |
| `latebra_batch_scrape` | Scrapes several URLs concurrently with a concurrency limit. | `urls` (required), `max_concurrent` (default 5) |
| `latebra_crawl` | Breadth-first crawl from a seed URL, following links. | `url` (required), `max_depth` (effective default 2), `max_pages` (effective default 20) |
| `latebra_search` | Web search through SearXNG or the built-in engines. | `query` (required), `max_results` (default 10) |
| `latebra_interact` | Drives a browser page: navigate, click, type. | `action` = `navigate` \| `click` \| `type` (required), `url`, `selector`, `text` |
| `latebra_check_anonymity` | Scrapes a detection page and reports which bot markers appear in the response. | `url` (default `https://httpbin.org/headers`) |
| `latebra_get_log_path` | Returns the absolute path of the log directory (for bug reports). | none |

Tool responses are JSON. `latebra_scrape` reports `status`, `layer_used` (`request` or `browser_*`), `content_length`, `timing_ms`, `title` and a content preview.

Browser tools require the `[browser]` extra and a browser binary; without them the pipeline records the layer error and returns `status: "error"` instead of crashing.

## CLI

```bash
latebra --version        # latebra 0.2.0
latebra run              # start the MCP server (default command)
latebra install          # post-install setup: Patchright Chromium + Camoufox binaries
```

## Production

Build the distributable wheel and run it as an installed artifact:

```bash
uv build                                   # -> dist/latebra-0.2.0-py3-none-any.whl (+ sdist)
uv venv /opt/latebra/.venv --python 3.12
uv pip install --python /opt/latebra/.venv/bin/python dist/latebra-0.2.0-py3-none-any.whl
/opt/latebra/.venv/bin/python -m latebra run   # or: latebra-mcp
```

The wheel install was verified end to end: fresh venv, wheel install, `initialize` + `tools/list` handshake returns the 8 tools, `latebra_get_log_path` answers.

Operational notes:

- the process speaks JSON-RPC on stdin/stdout, so it is meant to be launched by the MCP client, not as a daemon;
- logs go to `~/.local/share/latebra/logs` (rotating; path available through `latebra_get_log_path`);
- the SQLite cache lives in `~/.cache/latebra`;
- no Docker image is published and the repository has no Dockerfile;
- no PyPI release yet; distribute the wheel or install from source.

## Project structure

```
src/latebra/
├── server.py          MCP server: 8 tool definitions + dispatch
├── pipeline.py        SmartScrapePipeline: layered decision per URL
├── config.py          LatebraConfig.from_env (LATEBRA_* variables)
├── constants.py       thresholds, user agents, fingerprints, timeouts
├── layers/
│   ├── request.py     curl_cffi HTTP layer
│   ├── browser.py     Patchright / Camoufox / nodriver layer
│   ├── extraction.py  SQLite cache + extraction
│   ├── crawler.py     BFS crawler
│   ├── interact.py    navigate / click / type
│   ├── search.py      SearXNG with auto-detection and fallback
│   └── search_builtin.py  DuckDuckGo / Google / Bing engines (ddgs)
├── proxy/manager.py   rotation + circuit breaker
├── stealth/           fingerprint randomization, behavior simulation
├── captcha/solver.py  2Captcha / Capsolver clients
├── validation.py      SSRF-oriented URL validation (blocks private ranges)
├── log_utils.py       rotating file logs
└── install.py         `latebra install` post-setup
tests/                 unit, layer and performance suites (183 tests collected)
docs/                  SDD, performance baseline, plans and specs
```

## Verification

Facts measured on 2026-09-14 (Manjaro Linux, Python 3.12.14, repo at `1f9409e`, `mcp` 1.30.0):

| Check | Command | Result |
|---|---|---|
| Import and CLI | `latebra --version` | `latebra 0.2.0` |
| MCP handshake | `initialize` + `tools/list` + `latebra_get_log_path` over stdio | OK, 8 tools, tool call answered |
| Offline test subset | `pytest tests/ -m "not slow" --ignore=tests/performance --ignore=tests/test_search_builtin.py --ignore=tests/test_p0_features.py --ignore=tests/test_layers_search.py` | 113 passed in 0.92s |
| Full suite | `pytest tests/ -m "not slow"` | 166 selected (183 collected, 17 slow deselected): 163 passed, 2 failed, 1 skipped |
| Wheel build | `uv build` | `dist/latebra-0.2.0-py3-none-any.whl` produced and installed in a fresh venv |
| Browser fallback | batch tests hitting small pages | nodriver drove the system Chrome successfully |
| Lint | `ruff check src/ tests/` | 116 findings (open) |
| Types | `mypy src/` | 45 errors under strict mode (open) |

The 2 failing tests are external-search-engine dependent: `test_google_engine_returns_results` (Google returned no results from the audited network) and `test_search_latency` (measured 9.5s and 22s against a 5s threshold while engines timed out). The skipped test needs a running SearXNG on `localhost:8090` (optional service) and skips itself when absent. Everything else, including the crawl, batch, browser-fallback and stealth suites, passed.

## Current state and limitations

- No CI configured and no PyPI release: `uvx latebra` and `pip install latebra` do not work; install from source or from the built wheel.
- The test suite is not hermetic. Search tests call real search engines (they fail under rate limiting, as observed in the audit), and crawl/batch tests call `httpbin.org`.
- `config.py` parses the full `LATEBRA_*` set, but the server wires only `LATEBRA_PROXIES`, `LATEBRA_2CAPTCHA_KEY`, `LATEBRA_CAPSOLVER_KEY` and `LATEBRA_SEARCH_BACKEND`. Cache, stealth and timeout settings are parsed but not applied to the pipeline yet.
- The SearXNG URL is a fixed default (`http://localhost:8090`); there is no environment variable for it, only the constructor argument `LatebraServer(searxng_url=...)`.
- `mcp` is pinned to `>=1.0.0,<2.0.0`: SDK 2.x removed the `list_tools`/`call_tool` server API this code uses, so 1.x is required until the server is migrated.
- Browser engines Patchright and Camoufox need their binaries downloaded by `latebra install`; only nodriver works with a plain system Chrome.
- Lint and type debt is open (116 ruff findings, 45 mypy strict errors); nothing blocks runtime.
- `install.sh` / `install.ps1` are provided but were not executed in this audit (they install to `~/.latebra` and edit the Claude Desktop config).
- README translations (`README.pt-BR.md`, `README.es.md`, `README.ja.md`, `README.zh.md`) exist and may lag behind this document.

## Documentation

| Document | Content |
|---|---|
| [`docs/SDD.md`](docs/SDD.md) | Spec-driven development plan and components |
| [`docs/PERFORMANCE_BASELINE.md`](docs/PERFORMANCE_BASELINE.md) | Performance baseline measurements (2026-05-31) |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | Implementation plans (logging system, search backend) |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Design specs |
| [`AGENTS.md`](AGENTS.md) | Project layout notes for AI coding agents |

## License

MIT, see [`LICENSE`](LICENSE). Copyright (c) 2026 Evandro Fonseca Junior.
