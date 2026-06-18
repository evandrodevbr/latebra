# 🕶️ latebra

<div align="center">

**The most private anti-bot MCP server for AI agents.**
*Bypass Cloudflare, DataDome, Akamai — with maximum anonymity.*

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-149%20passed-brightgreen.svg)](https://github.com/evandrofjs/latebra/actions)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Search](https://img.shields.io/badge/search-built--in%20%2B%20SearXNG-green.svg)](#search)

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
| **Self-hosted search** | ✅ SearXNG + built-in fallback | ❌ | ❌ | ❌ |
| **Proxy rotation** | ✅ circuit breaker | ❌ | ✅ cloud | ❌ |
| **Browser engines** | ✅ 3 (Patchright/Camoufox/Nodriver) | ❌ 0 | ❌ 0 | ✅ 1 |
| **Fingerprint spoofing** | ✅ Canvas/WebGL/WebRTC | ❌ | ❌ | ❌ |
| **Anonymity check** | ✅ built-in tool | ❌ | ❌ | ❌ |
| **Zero cloud dependency** | ✅ 100% local | ❌ | ❌ | ✅ |
| **Preço** | ✅ **Grátis** | 💰 $19+/mês | 💰 $500+/mês | ✅ Grátis |

---

## 🚀 Quick Start

```bash
# Via pip (modo desenvolvimento)
git clone https://github.com/evandrodevbr/latebra.git && cd latebra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"

# Ou via uvx (zero-install)
uvx latebra

# Run — funciona imediatamente SEM search engine configurado
python -m latebra run
```

> 💡 **Sem SearXNG? Sem problema.** O latebra detecta automaticamente se o SearXNG está rodando. Se não estiver, faz fallback transparente para **DuckDuckGo + Google + Bing** via biblioteca nativa `ddgs` — sem container, sem configuração, sem API key.

### Configure no seu cliente MCP

<details open>
<summary><b>Hermes Agent</b></summary>

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  latebra:
    # Opção 1: usando uvx (recomendado)
    command: uvx
    args: [latebra]
    # Nota: nenhuma env var de search é necessária.
    # O fallback built-in funciona out-of-the-box.

    # Opção 2: usando python direto
    # command: python
    # args: [-m, latebra, run]
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

```json
// Invocação MCP:
{"tool": "latebra_scrape", "arguments": {"url": "https://news.ycombinator.com"}}

// Resposta:
{
  "status": "success",
  "layer_used": "request",        // ← bypassou Cloudflare com curl_cffi!
  "content_length": 35496,
  "timing_ms": 792,
  "title": "Hacker News"
}
```

### `latebra_search`
**Busca web privada via SearXNG com fallback automático para DuckDuckGo/Google/Bing (built-in).**
**Funciona sem nenhuma configuração — sem SearXNG, sem Docker, sem API key.**

```json
// Invocação MCP:
{"tool": "latebra_search", "arguments": {"query": "inteligencia artificial 2026", "max_results": 5}}

// Resposta (exemplo):
{
  "results": [
    {"title": "...", "url": "...", "snippet": "..."},
    ...
  ],
  "total_ms": 863
}
```

### `latebra_crawl`
**Deep crawl com BFS: descobre e mapeia sites automaticamente.**

```json
// Invocação MCP:
{"tool": "latebra_crawl", "arguments": {"url": "https://docs.python.org/3/", "max_depth": 2, "max_pages": 50}}
// → Navega até 2 níveis de profundidade, coleta até 50 páginas
```

### `latebra_batch_scrape`
**Múltiplas URLs em paralelo com controle de concorrência.**

```json
// Invocação MCP:
{
  "tool": "latebra_batch_scrape",
  "arguments": {
    "urls": ["https://api.github.com", "https://httpbin.org/ip", "https://news.ycombinator.com"],
    "max_concurrent": 5
  }
}
// → 3 URLs em paralelo, ~1.9s por URL com concorrência controlada
```

### `latebra_interact`
**Click, type, navigate — interaja com SPAs e formulários.**

```json
// Navegar:
{"tool": "latebra_interact", "arguments": {"action": "navigate", "url": "https://example.com/login"}}

// Clicar:
{"tool": "latebra_interact", "arguments": {"action": "click", "selector": "button.submit"}}

// Digitar:
{"tool": "latebra_interact", "arguments": {"action": "type", "selector": "input[name=email]", "text": "user@example.com"}}
```

### `latebra_scrape_with_browser`
**Força browser mode (Patchright/Camoufox/Nodriver).**

```json
{"tool": "latebra_scrape_with_browser", "arguments": {"url": "https://spa.example.com", "browser": "camoufox"}}
```

### `latebra_check_anonymity`
**Verifica se você está sendo detectado como bot.**

```json
{"tool": "latebra_check_anonymity", "arguments": {"url": "https://browserscan.net"}}
// → Retorna quais markers de detecção foram encontrados
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
   │ SearXNG ─║─auto─fallback→ 3 layers  │         │    BFS     │
   │  ║       │          └──────┬───────┘         └────────────┘
   │  ▼       │                    │
   │ Built-in │                    │
   │DDG/Google│                    │
   │  /Bing   │                    │
   └──────────┘                    │
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
| `latebra_batch_scrape` (3 URLs) | **1.9s/URL** (concorrente) | ~3 req/s |
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

### SearXNG (Search Backend — Opcional)

O latebra funciona **sem nenhum search engine configurado**. Por padrão (`auto`), ele:

1. Tenta conectar no SearXNG em `http://localhost:8090`
2. Se não encontrar, faz **fallback automático** para **DuckDuckGo + Google + Bing** via biblioteca `ddgs`
3. Você também pode forçar `built-in` com `LATEBRA_SEARCH_BACKEND=built-in` para pular a detecção

Para quem quiser máximas privacidade e zero tracking, recomenda-se rodar SearXNG local:

```bash
docker run -d --name searxng -p 8090:8080 searxng/searxng:latest
# Configure o endpoint (opcional — default já é localhost:8090):
export SEARXNG_URL="http://localhost:8090"
```

> 🛡️ Com SearXNG, você usa os mesmos engines (Google, DDG, Bing, Qwant) sem expor seu IP ou cookies de tracking.

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
| `LATEBRA_SEARCH_BACKEND` | Modo de busca: `auto` (fallback), `searxng`, `built-in` | `auto` |
| `SEARXNG_URL` | URL do SearXNG (opcional — só usado se `auto` detectar ou `searxng` forçado) | `http://localhost:8090` |
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
git clone https://github.com/evandrodevbr/latebra.git
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
