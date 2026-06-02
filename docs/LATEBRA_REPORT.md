# Latebra — Relatório Técnico Completo

**Versão:** 0.2.0  
**Data:** 2026-06-02  
**Autor:** Evandro Fonseca Junior  
**Repositório:** https://github.com/evandrodevbr/latebra

---

## 1. Visão Geral

Latebra é um servidor MCP (Model Context Protocol) para scraping web com maximum anonimidade. Implementa uma pipeline de 3 camadas para evasão de anti-bot, permitindo que agentes de IA como o Hermes realizem web scraping em sites protegidos por Cloudflare, DataDome, e outros sistemas anti-bot.

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Client (Hermes)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ JSON-RPC
┌──────────────────────────▼──────────────────────────────────┐
│                    latebra MCP Server                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  8 Ferramentas MCP:                                 │   │
│  │  • latebra_scrape           (pipeline inteligente)  │   │
│  │  • latebra_scrape_with_browser (browser forçado)    │   │
│  │  • latebra_check_anonymity  (detecção anti-bot)     │   │
│  │  • latebra_search           (SearXNG)               │   │
│  │  • latebra_crawl            (BFS deep crawl)        │   │
│  │  • latebra_batch_scrape     (concorrente)           │   │
│  │  • latebra_interact         (click/type/navigate)   │   │
│  │  • latebra_get_log_path     (debug logs)            │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 SmartScrapePipeline                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: AsyncRequestLayer (curl_cffi)                     │
│  • TLS impersonation (Chrome 120/124)                       │
│  • Bypass Cloudflare via fingerprint matching               │
│  • Proxy rotation + circuit breaker                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: AsyncBrowserLayer (fallback chain)                │
│  • Patchright (Playwright stealth fork)                     │
│  • Camoufox (Firefox anti-fingerprint)                      │
│  • Nodriver (Chrome DevTools Protocol)                      │
│  • Warm pool para reduzir latência                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: AsyncExtractionLayer (Crawl4AI)                   │
│  • Extração de conteúdo via CSS/XPath                       │
│  • Cache SQLite WAL mode                                    │
│  • Deduplicação automática                                  │
├─────────────────────────────────────────────────────────────┤
│  SearchLayer: SearXNG (busca web privada)                   │
│  CrawlerLayer: BFS com link extraction                      │
│  InteractLayer: Ações em SPAs                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Requisitos

### 3.1 Sistema
- **Python:** 3.12+
- **SO:** Linux, macOS, Windows (WSL recomendado)
- **RAM:** 2GB mínimo (4GB recomendado com browsers)
- **Disco:** 500MB para dependências + browsers

### 3.2 Dependências Principais

| Pacote | Versão | Função |
|--------|--------|--------|
| `curl-cffi` | >=0.7.0 | HTTP com TLS impersonation |
| `httpx` | >=0.27.0 | HTTP client async |
| `mcp` | >=1.0.0 | SDK do Model Context Protocol |
| `patchright` | >=1.0.0 | Browser stealth (Playwright fork) |
| `camoufox` | >=0.2.0 | Browser anti-fingerprint (Firefox) |
| `nodriver` | >=0.38.0 | Browser via CDP |
| `crawl4ai` | >=0.4.0 | Extração de conteúdo |

### 3.3 Serviços Externos

| Serviço | Porta | Função | Obrigatório? |
|---------|-------|--------|--------------|
| SearXNG | 8090 | Busca web privada | Sim (para `latebra_search`) |
| 2captcha/capsolver | API | Resolução de captcha | Não (opcional) |

---

## 4. Instalação

### 4.1 Instalação Padrão

```bash
cd /home/evandro/latebra
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

### 4.2 Para Hermes Agent

O pacote é instalado em um venv dedicado:

```bash
# Venv do Hermes para latebra
/home/evandro/.hermes/venvs/latebra/bin/python -m pip install -e "/home/evandro/latebra[all]"
```

### 4.3 Configuração no Hermes

Em `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  latebra:
    command: /home/evandro/.hermes/venvs/latebra/bin/python
    args:
      - -m
      - latebra
      - run
    env:
      SEARXNG_URL: http://localhost:8090
    enabled: true
```

### 4.4 Setup SearXNG

```bash
# Criar config
mkdir -p /tmp/searxng-config
cat > /tmp/searxng-config/settings.yml << 'YAML'
use_default_settings: true
search:
  formats:
    - html
    - json
server:
  secret_key: "latebra-dev-searxng-key"
  bind_address: "0.0.0.0"
  limiter: false
YAML

# Iniciar container
docker run -d --name searxng \
  -p 8090:8080 \
  -v /tmp/searxng-config/settings.yml:/etc/searxng/settings.yml:ro \
  searxng/searxng:latest
```

---

## 5. Search Engines

### 5.1 Padrão (SearXNG)

O SearXNG é um metadorador que agrega resultados de múltiplos engines:

**Engines ativos por padrão:**
- **Google** — Resultados principais
- **DuckDuckGo** — Privacidade, resultados alternativos
- **Wikipedia** — Informação enciclopédica

**Engines disponíveis (podem ser ativados):**
- Bing, Yahoo, Qwant, Startpage
- Brave Search, Mojeek, Yep
- arXiv, PubMed (acadêmicos)
- GitHub, GitLab (código)
- YouTube, Vimeo (vídeo)
- Reddit, Stack Overflow (discussão)

### 5.2 Como Mudar Engines

```python
# Buscar apenas no Google
await search.search("query", engines="google")

# Buscar em engines específicos
await search.search("query", engines="google,duckduckgo,bing")

# Buscar em categorias
await search.search("query", categories="general,images")
```

### 5.3 Vantagens do SearXNG

1. **Privacidade:** Não rastreia usuários
2. **Anti-bloqueio:** Distribui requests entre engines
3. **Self-hosted:** Controle total sobre dados
4. **JSON API:** Fácil integração com MCP

---

## 6. Fluxo de Trabalho do Pipeline

### 6.1 Scrape Inteligente (`latebra_scrape`)

```
URL recebida
    │
    ▼
validate(url) ─── Bloqueia IPs privados, metadata AWS
    │
    ▼
Layer 1: curl_cffi
    │
    ├─ Sucesso (200 + len > 500 bytes) → Retorna resultado
    │
    └─ Falha ou conteúdo suspeito
        │
        ▼
    Terminal error check (DNS/conexão)
        │
        ├─ Erro terminal → Retorna erro imediatamente
        │
        └─ Não é terminal
            │
            ▼
        Layer 2: Browser (fallback chain)
            │
            ├─ PARALLEL_FALLBACK=True: Race todos engines
            │
            └─ PARALLEL_FALLBACK=False (default): Serial
                │
                ├─ Patchright
                ├─ Camoufox
                └─ Nodriver
                    │
                    ▼
                Layer 3: Crawl4AI extraction
                    │
                    ▼
                Retorna resultado
```

### 6.2 Scrape com Browser Forçado (`latebra_scrape_with_browser`)

Pula Layer 1 e vai direto para Layer 2 com o engine especificado.

### 6.3 Busca Web (`latebra_search`)

```
Query recebida
    │
    ▼
SearchLayer.search()
    │
    ▼
HTTP GET → SearXNG API (localhost:8090/search)
    │
    ▼
Parse JSON → Lista de resultados
```

---

## 7. Ferramentas MCP Disponíveis

| Ferramenta | Descrição | Uso Principal |
|------------|-----------|---------------|
| `latebra_scrape` | Pipeline inteligente 3-layer | Scraping geral |
| `latebra_scrape_with_browser` | Força modo browser | Sites com JS pesado |
| `latebra_check_anonymity` | Verifica detecção anti-bot | Debug de bloqueios |
| `latebra_search` | Busca via SearXNG | Pesquisa web privada |
| `latebra_crawl` | Crawl BFS profundo | Múltiplas páginas |
| `latebra_batch_scrape` | Scraping concorrente | Muitas URLs |
| `latebra_interact` | Click/type/navigate | SPAs interativas |
| `latebra_get_log_path` | Caminho dos logs | Debug/issue reporting |

---

## 8. Onde Instala

### 8.1 Estrutura de Arquivos

```
/home/evandro/latebra/
├── src/latebra/           # Código fonte
│   ├── server.py          # Entry point MCP
│   ├── pipeline.py        # Orquestrador principal
│   ├── layers/
│   │   ├── request.py     # curl_cffi
│   │   ├── browser.py     # 3 engines browser
│   │   ├── extraction.py  # Crawl4AI
│   │   ├── search.py      # SearXNG
│   │   ├── crawler.py     # BFS crawl
│   │   └── interact.py    # Ações browser
│   ├── proxy/manager.py   # Proxy rotation
│   ├── stealth/           # Fingerprint/behavior
│   └── captcha/solver.py  # 2captcha/capsolver
├── tests/                 # 149+ testes
├── .venv/                 # Virtual env do projeto
└── pyproject.toml         # Config do projeto
```

### 8.2 Locais de Instalação

| Componente | Local |
|------------|-------|
| Código fonte | `/home/evandro/latebra/src/latebra/` |
| Venv Hermes | `/home/evandro/.hermes/venvs/latebra/` |
| Venv projeto | `/home/evandro/latebra/.venv/` |
| Logs | `/home/evandro/.local/share/latebra/logs/` |
| Cache | SQLite WAL mode no diretório de dados |
| SearXNG | Docker container `searxng` (porta 8090) |
| Browsers | `~/.cache/patchright/`, `~/.cache/camoufox/` |

---

## 9. Fix Aplicado (2026-06-02)

### Problema
O servidor MCP iniciava mas falhava com:
```
'dict' object has no attribute 'name'
```

### Causa Raiz
O SDK MCP (v1.26+) exige que `list_tools()` retorne `list[mcp.types.Tool]`, não `list[dict]`.

### Solução
Em `src/latebra/server.py`:

```python
from mcp.types import Tool

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"],
        )
        for t in latebra.tool_definitions
    ]
```

### Resultado
- ✅ 8 ferramentas registradas corretamente
- ✅ Conexão MCP estabelecida
- ✅ Todos os testes passando

---

## 10. Comandos Úteis

```bash
# Testar servidor
cd /home/evandro/latebra
.venv/bin/python -m latebra run

# Rodar testes
.venv/bin/pytest tests/ -v -m "not slow"

# Verificar SearXNG
curl "http://localhost:8090/search?q=test&format=json"

# Ver logs
tail -f /home/evandro/.local/share/latebra/logs/latebra.log
cat /home/evandro/.local/share/latebra/logs/errors.log
```

---

## 11. Status Atual

| Componente | Status |
|------------|--------|
| Servidor MCP | ✅ Funcional |
| Ferramentas | ✅ 8/8 registradas |
| SearXNG | ✅ Rodando (Docker) |
| Engines search | ✅ Google, DuckDuckGo, Wikipedia |
| Patchright | ✅ Instalado |
| Camoufox | ✅ Instalado |
| Nodriver | ✅ Instalado |
| Crawl4AI | ✅ Instalado |
| Testes | ✅ 25/25 core passando |
| Hermes integration | ✅ Configurado |

---

**Relatório gerado em:** 2026-06-02  
**Autor:** Evandro Fonseca Junior  
**Licença:** MIT
