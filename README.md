# 🕶️ latebra

<div align="center">

**The most private anti-bot MCP server for AI agents.**
*Bypass Cloudflare, DataDome, Akamai — with maximum anonymity.*

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-149%20passed-brightgreen.svg)](https://github.com/evandrofjs/latebra/actions)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/SearXNG-ready-orange.svg)](#search)

<br>

> **latebra** (latim: *esconderijo*) — uma pipeline de 3 camadas de evasão anti-bot.
> Do TLS fingerprint à simulação comportamental, tudo rodando local com zero dependência de cloud.

</div>

---

## ✨ Por que latebra?

| | latebra | Firecrawl | Brightdata | Playwright MCP |
|---|---|---|---|---|
| **3-layer evasion** | ✅ TLS→Browser→Extract | ❌ | ❌ | ❌ |
| **TLS impersonation** | ✅ curl_cffi (Chrome 120/124) | ❌ | ❌ | ❌ |
| **Cloudflare bypass** | ✅ testado em produção | ✅ cloud | ✅ cloud | ❌ |
| **Self-hosted search** | ✅ SearXNG privado | ❌ | ❌ | ❌ |
| **Proxy rotation** | ✅ circuit breaker | ❌ | ✅ cloud | ❌ |
| **Browser engines** | ✅ 3 (Patchright/Camoufox/Nodriver) | ❌ 0 | ❌ 0 | ✅ 1 |
| **Fingerprint spoofing** | ✅ Canvas/WebGL/WebRTC | ❌ | ❌ | ❌ |
| **Anonymity check** | ✅ built-in tool | ❌ | ❌ | ❌ |
| **Zero cloud dependency** | ✅ 100% local | ❌ | ❌ | ✅ |
| **Preço** | ✅ **Grátis** | 💰 $19+/mês | 💰 $500+/mês | ✅ Grátis |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/evandrofjs/latebra.git && cd latebra

# Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"

# Start SearXNG (search backend)
docker run -d --name searxng -p 8090:8080 searxng/searxng:latest

# Run
python -m latebra run
```

### Configure no seu cliente MCP

<details open>
<summary><b>Hermes Agent</b></summary>

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  latebra:
    command: python
    args: [-m, latebra, run]
    env:
      SEARXNG_URL: http://localhost:8090
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

```json
{
  "mcpServers": {
    "latebra": {
      "command": "python",
      "args": ["-m", "latebra", "run"],
      "env": {
        "PROXY_LIST": "socks5://user:pass@proxy:1080",
        "CAPSOLVER_API_KEY": "your_key"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

```json
{
  "mcpServers": {
    "latebra": {
      "command": "python",
      "args": ["-m", "latebra", "run"]
    }
  }
}
```
</details>

---

## 🔧 Ferramentas MCP (7 tools)

### `latebra_scrape`
**Pipeline inteligente: curl_cffi → browser fallback automático.**

```python
# O agente chama:
latebra_scrape(url="https://news.ycombinator.com")

# Resposta:
{
  "status": "success",
  "layer_used": "request",        # ← bypassou Cloudflare com curl_cffi!
  "content_length": 35496,
  "timing_ms": 792,
  "title": "Hacker News"
}
```

### `latebra_search`
**Busca web privada via SearXNG (sem tracking, sem ads, sem rate limit).**

```python
latebra_search(query="inteligencia artificial 2026", max_results=5)
# → 5 resultados em ~860ms
```

### `latebra_crawl`
**Deep crawl com BFS: descobre e mapeia sites automaticamente.**

```python
latebra_crawl(url="https://docs.python.org/3/", max_depth=2, max_pages=50)
# → Navega até 2 níveis de profundidade, coleta até 50 páginas
```

### `latebra_batch_scrape`
**Múltiplas URLs em paralelo com controle de concorrência.**

```python
latebra_batch_scrape(
  urls=["https://api.github.com", "https://httpbin.org/ip"],
  max_concurrent=5
)
# → 3 URLs em ~5.8s com concorrência controlada
```

### `latebra_interact`
**Click, type, navigate — interaja com SPAs e formulários.**

```python
# Navegar
latebra_interact(action="navigate", url="https://example.com/login")

# Clicar
latebra_interact(action="click", selector="button.submit")

# Digitar
latebra_interact(action="type", selector="input[name=email]", text="user@example.com")
```

### `latebra_scrape_with_browser`
**Força browser mode (Patchright/Camoufox/Nodriver).**

```python
latebra_scrape_with_browser(url="https://spa.example.com", browser="camoufox")
```

### `latebra_check_anonymity`
**Verifica se você está sendo detectado como bot.**

```python
latebra_check_anonymity(url="https://browserscan.net")
# → Retorna quais markers de detecção foram encontrados
```

---

## 🏗️ Arquitetura

```
                    ┌─────────────────────────┐
                    │     MCP Client           │
                    │  (Claude, Cursor, Hermes)│
                    └───────────┬─────────────┘
                                │ JSON-RPC
                    ┌───────────▼─────────────┐
                    │     server.py            │
                    │  7 MCP tools registradas │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼─────┐          ┌──────▼──────┐         ┌─────▼──────┐
   │  SEARCH  │          │   PIPELINE   │         │   CRAWL    │
   │ SearXNG  │          │  3 layers    │         │    BFS     │
   └──────────┘          └──────┬───────┘         └────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
       ┌────▼────┐        ┌─────▼─────┐       ┌─────▼──────┐
       │ LAYER 1 │──fallback→│ LAYER 2  │──fallback→│ LAYER 3  │
       │ curl_cffi│        │ Browser   │       │ Crawl4AI  │
       │ TLS imp. │        │ Patchright│       │ + cache    │
       └────┬─────┘        │ Camoufox  │       └────────────┘
            │              │ Nodriver  │
            │              └─────┬─────┘
            │                    │
       ┌────▼────────────────────▼─────┐
       │     MÓDULOS AUXILIARES         │
       │  ┌──────────┐ ┌─────────────┐ │
       │  │  PROXY   │ │   STEALTH   │ │
       │  │ rotation │ │ fingerprint │ │
       │  │ circuit  │ │  behavior   │ │
       │  │ breaker  │ │  canvas     │ │
       │  └──────────┘ └─────────────┘ │
       │  ┌──────────┐                 │
       │  │ CAPTCHA  │                 │
       │  │ 2Captcha │                 │
       │  │ Capsolver│                 │
       │  └──────────┘                 │
       └───────────────────────────────┘
```

### Pipeline de decisão

```
Início
  │
  ▼
┌─────────────┐    sucesso    ┌──────────┐
│ curl_cffi   │──────────────→│ Extração │
│ (TLS spoof) │               │ Crawl4AI │
└──────┬──────┘               └──────────┘
       │ falha
       ▼
┌─────────────┐
│ É erro de   │──sim──→ Retorna erro (DNS, conexão)
│ rede?       │
└──────┬──────┘
       │ não (provavelmente bloqueado)
       ▼
┌─────────────┐
│ Patchright  │──sucesso──→ Extração
└──────┬──────┘
       │ falha
       ▼
┌─────────────┐
│ Camoufox    │──sucesso──→ Extração
└──────┬──────┘
       │ falha
       ▼
┌─────────────┐
│ Nodriver    │──sucesso──→ Extração
└──────┬──────┘
       │ falha
       ▼
   ❌ erro
```

---

## 📊 Performance

### Benchmarks reais (2026-05-31)

| Operação | Latência | Throughput |
|---|---|---|
| `latebra_scrape` (curl_cffi) | **142ms avg** | ~7 req/s |
| `latebra_search` (5 resultados) | **863ms** | — |
| `latebra_crawl` (depth=0) | **485ms** | — |
| `latebra_batch_scrape` (3 URLs) | **5.870ms** (total) | concorrente |
| Hacker News (Cloudflare) | **792ms** ✅ bypass | curl_cffi |
| Wikipedia | **189ms** | 166KB |
| Memória 100 ops | **+0.4MB** | sem leak |

### Comparativo de latência

```
latebra (curl_cffi)  ████████░░ 142ms
Firecrawl (cloud)    ██████████████ 800-2000ms
Playwright MCP       ████████████████████████ 3000-8000ms
Brightdata           ██████████ 500-1500ms
```

---

## 🛡️ Técnicas de Evasão

| Técnica | Implementação | Eficácia |
|---|---|---|
| **TLS Fingerprinting** | JA3/JA4 impersonation via curl_cffi | Cloudflare ✅ |
| **Canvas Fingerprinting** | Ruído aleatório no renderer Canvas 2D | Browserscan ✅ |
| **WebGL Fingerprinting** | Spoofing de vendor/renderer WebGL | Pixelscan ✅ |
| **WebRTC Leak** | Prevenção de vazamento de IP real | ipleak.net ✅ |
| **Behavior Simulation** | Curvas de Bezier, delays humanos, scroll natural | DataDome ✅ |
| **Proxy Rotation** | Round-robin + circuit breaker automático | Rate limit ✅ |
| **CDP Detection** | Remoção de flags detectáveis do Chrome DevTools | Akamai ✅ |
| **Rate Limit Bypass** | Distribuição de requests entre múltiplos proxies | — |
| **Honeypot Detection** | Identificação de links-armadilha invisíveis | — |
| **CAPTCHA Solving** | 2Captcha + Capsolver com fallback | reCAPTCHA ✅ |

---

## 🔌 Integrações

### Proxy Services
```bash
export PROXY_LIST="socks5://user:pass@proxy1:1080,socks5://user:pass@proxy2:1080"
```

### CAPTCHA Solvers
```bash
export CAPSOLVER_API_KEY="CAP-..."     # Capsolver
export TWOCAPTCHA_API_KEY="abc123..."  # 2Captcha
```

### SearXNG (Search Backend)
```bash
docker run -d --name searxng -p 8090:8080 searxng/searxng:latest
# Configure o endpoint:
export SEARXNG_URL="http://localhost:8090"
```

---

## 🧪 Desenvolvimento

```bash
# Rodar todos os testes (sem browser)
pytest tests/ -v -m "not slow"          # 149 testes, ~22s

# Testes de performance
pytest tests/performance/ -v -s -m "not slow"

# Testes com browser (requer Patchright/Camoufox/Nodriver)
pytest tests/ -v

# Lint
ruff check src/ tests/
mypy src/
```

### Estrutura de testes

```
tests/
├── test_layers_request.py       ← HTTP layer
├── test_layers_browser.py       ← Browser engines
├── test_layers_extraction.py    ← Crawl4AI + cache
├── test_pipeline.py             ← Orquestrador
├── test_server.py               ← MCP server
├── test_p0_features.py          ← Search, crawl, batch, interact
├── test_proxy_manager.py        ← Proxy rotation
├── test_captcha_solver.py       ← CAPTCHA
├── test_stealth_*.py            ← Fingerprint + behavior
├── test_validation.py           ← URL validation
└── performance/                 ← Bateria de performance
    ├── conftest.py              ← Thresholds + fixtures
    ├── test_scrape_latency.py   ← Latência por camada
    ├── test_browser_bootstrap.py ← Cold/warm boot
    ├── test_mcp_throughput.py   ← Carga concorrente
    ├── test_memory_stability.py ← Leak detection
    ├── test_anonymity_efficacy.py ← Taxa de bypass
    ├── test_p0_performance.py   ← Search/crawl/batch benchmarks
    └── test_compiled_regex.py   ← Micro-optimizations
```

---

## 📦 Instalação Avançada

```bash
# Mínimo (MCP + HTTP)
pip install -e .

# Com browser
pip install -e ".[browser]"

# Com extração
pip install -e ".[extraction]"

# Com CAPTCHA
pip install -e ".[captcha]"

# Completo
pip install -e ".[all]"

# Desenvolvimento
pip install -e ".[all,dev]"
```

---

## 🌍 Environment Variables

| Variável | Descrição | Default |
|---|---|---|
| `SEARXNG_URL` | URL do SearXNG | `http://localhost:8090` |
| `PROXY_LIST` | Lista de proxies (vírgula) | — |
| `CAPSOLVER_API_KEY` | API key Capsolver | — |
| `TWOCAPTCHA_API_KEY` | API key 2Captcha | — |
| `LATEBRA_PERF_TEST_URL` | URL para testes de perf | `https://httpbin.org/html` |

---

## 🗺️ Roadmap

- [x] **v0.1** — Pipeline 3-layer (TLS → Browser → Extract)
- [x] **v0.2** — Proxy rotation, stealth, CAPTCHA, cache SQLite
- [x] **v0.3** — Search (SearXNG), crawl, batch, interact, 10 otimizações de performance
- [ ] **v0.4** — Markdown output nativo, screenshot, rate limiting, retry exponencial, session persistence
- [ ] **v0.5** — Streamable HTTP + SSE, geographic targeting, webhook, content diff, dashboard web

---

## 🤝 Contribuindo

```bash
git clone https://github.com/evandrofjs/latebra.git
cd latebra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all,dev]"
pytest tests/ -v
```

Abra uma issue antes de enviar PRs grandes. Seguimos [Conventional Commits](https://www.conventionalcommits.org/).

---

## 📚 Referências

- COOK, Garrett, et al. *There's a Hole in the Bucket: Large-Scale Analysis of CAPTCHA Abuse*. 2020.
- VASTEL, Antoine. *Modern Fingerprinting Techniques: A Survey*. 2017.
- LAPERDRIX, Pierre, et al. *Beauty and the Beast: Diverting Modern Web Browsers from Building Honest Fingerprints*. 2016.
- ACAR, Gunes, et al. *The Web Never Forgets: Persistent Tracking Mechanisms in the Wild*. 2014.

---

## ⚖️ Licensa

MIT © 2026 **Evandro Fonseca Junior**

---

<div align="center">
<br>
<sub>latebra — latim para "esconderijo". Porque na web moderna, privacidade é resistência.</sub>
</div>
