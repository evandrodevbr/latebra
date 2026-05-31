# latebra 🕵️‍♂️

**MCP server para anti-bot web scraping anônimo.**

Pipeline multi-camadas que combina TLS fingerprinting, browser stealth com simulação comportamental, proxy rotation e resolução de CAPTCHAs — tudo exposto como ferramentas MCP para agents (Claude, Hermes, etc.).

## Pipeline

```
Request (curl_cffi) → Browser (Playwright + Stealth) → Extraction (Crawl4AI / fallback)
                        ↓                              ↓
                 ProxyManager                    ContentCache (SQLite TTL)
                 CaptchaSolver
```

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                      latebra MCP Server                       │
├──────────────────────────────────────────────────────────────┤
│  ScrapeResult ← SmartScrapePipeline ← MCP tools              │
│                                                              │
│  Layer 1: request.py         curl_cffi + TLS impersonation   │
│  Layer 2: browser.py         Playwright + stealth init       │
│  Layer 3: extraction.py      Crawl4AI / regex fallback       │
│                                                              │
│  proxy/manager.py            Rotação, health check, auto-ban │
│  stealth/fingerprint.py      Canvas/WebGL/WebRTC spoofing    │
│  stealth/behavior.py         Bezier curves, delays, scroll   │
│  captcha/solver.py           2Captcha / Capsolver            │
└──────────────────────────────────────────────────────────────┘
```

## Instalação

```bash
git clone <repo-url> ~/latebra
cd ~/latebra
uv sync
# ou: python -m venv .venv && . .venv/bin/activate && pip install -e .
```

Dependências opcionais por funcionalidade:

| Funcionalidade | Dependência | Instalação |
|---|---|---|
| TLS impersonation | `curl_cffi` | incluída |
| Browser automation | `playwright` | `playwright install chromium` |
| Extração avançada | `crawl4ai` | `pip install crawl4ai` |
| Captcha solver | `capsolver` / `2captcha-python` | opcional |

## Uso (MCP)

```bash
# Iniciar servidor MCP
python -m latebra run
```

Conecte como MCP client (Hermes Agent, Claude Code, etc.) e use as ferramentas:

| Tool | Descrição |
|---|---|
| `scrape` | Scrape inteligente com fallback request→browser→extraction |
| `extract` | Extração de conteúdo de HTML já obtido |
| `health` | Status do servidor, cache hits, estatísticas |

### Exemplo via Hermes Agent (config.yaml)

```yaml
mcp_servers:
  latebra:
    command: python
    args: ["-m", "latebra", "run"]
    workdir: ~/latebra
```

### Exemplo via Python direto

```python
from latebra.pipeline import SmartScrapePipeline

pipeline = SmartScrapePipeline(proxies=["http://user:pass@host:8080"])
result = await pipeline.scrape("https://exemplo.com")
print(result.title, result.status, result.timing_ms)
```

## Técnicas Implementadas

- **TLS Fingerprinting** (JA3/JA4) via `curl_cffi` com impersonate de Chrome/Safari/Firefox
- **Browser Fingerprinting randomizado** — Canvas, WebGL, AudioContext, WebRTC spoofing
- **Stealth init script** — Remove `navigator.webdriver`, normaliza `window.chrome`, plugins, languages
- **Comportamento humano simulado** — Curvas de Bezier para mouse, delays gaussianos para typing, scroll natural
- **Proxy rotation** — Round-robin e aleatório, health check periódico, ban automático após N falhas
- **Captcha solving** — 2Captcha e Capsolver (por env vars)
- **Content cache** — SQLite com TTL, evita re-requests desnecessários
- **Fallback automático** — request → browser → extraction, cada camada tenta antes de escalar

## Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `CAPSOLVER_API_KEY` | API key do Capsolver |
| `TWOCAPTCHA_API_KEY` | API key do 2Captcha |
| `PROXY_LIST` | Lista de proxies separados por vírgula |

## Licença

MIT
