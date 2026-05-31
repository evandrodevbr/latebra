# latebra 🕵️

**MCP server anti-bot para web scraping anônimo com pipeline multi-camadas de evasão.**

latebra combina TLS fingerprinting, browser stealth, simulação comportamental humana, rotação de proxies e resolução de CAPTCHAs em um único servidor MCP. Cada camada opera com fallback automático: se a requisição HTTP falha por detecção, o pipeline escala para browser stealth; se o browser é bloqueado, tenta extração via crawler headless — sempre preservando o máximo de anonimidade.

---

## Pipeline

```
┌──────────┐    ┌───────────┐    ┌──────────────┐
│ REQUEST  │───▶│  BROWSER  │───▶│ EXTRACTION   │
│ curl_cffi │    │ Playwright│    │ Crawl4AI     │
│ TLS imp.  │    │ + stealth │    │ + regex      │
└────┬─────┘    └─────┬─────┘    └──────┬───────┘
     │                │                 │
     ▼                ▼                 ▼
┌──────────┐    ┌───────────┐    ┌──────────────┐
│  PROXY   │    │STEALTH    │    │   CACHE      │
│ Manager  │    │Fingerprint│    │  SQLite TTL  │
│ Rotation │    │ + Behavior│    │  Dedup       │
│ Health   │    │ Canvas    │    │              │
│ Check    │    │ WebGL     │    │              │
└──────────┘    └───────────┘    └──────────────┘
                     │
                     ▼
               ┌──────────┐
               │  CAPTCHA  │
               │  Solver   │
               │ 2Captcha  │
               │ Capsolver │
               └──────────┘
```

O pipeline segue uma estratégia de graceful degradation:

1. **Request** — tentativa inicial com `curl_cffi` e impersonação TLS
2. **Browser** — se detectionado, sobe Playwright com perfil stealth
3. **Extraction** — extrai o conteúdo com Crawl4AI ou regex de fallback
4. **Cache** — resultados armazenados em SQLite com TTL configurável

Módulos auxiliares (proxy, stealth, captcha) operam transversalmente em todas as camadas.

---

## Arquitetura

```
src/latebra/
│
├── server.py                # MCP server — tools: scrape, extract, health
│
├── pipeline.py              # SmartScrapePipeline — orquestrador com fallback
│
├── layers/
│   ├── request.py           # curl_cffi + impersonação TLS + proxy
│   ├── browser.py           # Playwright + inicialização stealth
│   └── extraction.py        # Crawl4AI + regex fallback + cache SQLite TTL
│
├── proxy/
│   └── manager.py           # Rotação de proxies, health check, ban automático
│
├── stealth/
│   ├── fingerprint.py       # Spoofing de Canvas, WebGL, WebRTC
│   └── behavior.py          # Curvas de Bezier, delays humanos, scroll natural
│
└── captcha/
    └── solver.py            # 2Captcha + Capsolver
```

### Fluxo de Execução

```
                  ┌─────────────────┐
                  │  MCP Client      │
                  │  (Hermes Agent)  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  server.py       │
                  │  scrape/extract  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  pipeline.py     │
                  │  fallback chain  │
                  └───┬───┬───┬─────┘
                      │   │   │
              ┌───────┘   │   └───────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌────────┐ ┌──────────┐
        │ request  │ │browser │ │extraction│
        │  curl_   │ │Playwr. │ │Crawl4AI  │
        │  cffi    │ │stealth │ │+ regex   │
        └──────────┘ └────────┘ └──────────┘
              │           │           │
              └───────────┴───────────┘
                          │
                          ▼
                  ┌─────────────────┐
                  │   SQLite Cache   │
                  │   (TTL + dedup)  │
                  └─────────────────┘
```

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/evandrofjs/latebra.git
cd latebra

# Instale com uv (recomendado)
uv sync

# Ou com pip em modo editável
pip install -e .

# Com suporte a todos os módulos (browser + extração)
pip install -e ".[all]"
```

### Dependências

O projeto é modular. Instale apenas o necessário:

- **Mínimo (MCP):** `pip install -e .`
- **+ Browser:** `pip install -e ".[browser]"`
- **+ Extração:** `pip install -e ".[extraction]"`
- **+ Captcha:** `pip install -e ".[captcha]"`
- **Completo:** `pip install -e ".[all]"`

---

## Uso

### Como MCP Server

```bash
python -m latebra run
```

Configure no seu MCP client (ex.: Hermes Agent, Claude Desktop):

```json
{
  "mcpServers": {
    "latebra": {
      "command": "python",
      "args": ["-m", "latebra", "run"],
      "env": {
        "PROXY_LIST": "socks5://user:pass@proxy1:1080,socks5://user:pass@proxy2:1080",
        "CAPSOLVER_API_KEY": "sua_chave_aqui"
      }
    }
  }
}
```

**Ferramentas disponíveis:**

- `scrape` — scraping inteligente com fallback HTTP → Browser
- `extract` — extração direta de conteúdo estruturado
- `health` — verificação de status e nível de anonimato

### Como Biblioteca Python

```python
import asyncio
from latebra.pipeline import SmartScrapePipeline

async def main():
    pipeline = SmartScrapePipeline(
        proxy_list=["socks5://user:pass@proxy1:1080"],
        capsolver_key="sua_chave",
    )

    resultado = await pipeline.scrape(
        url="https://exemplo.com",
        force_browser=False,     # tenta HTTP primeiro
        extract_structured=True, # extrai com Crawl4AI
    )

    print(f"Status: {resultado.status}")
    print(f"Conteúdo: {resultado.content[:500]}")
    print(f"Camada usada: {resultado.layer}")

asyncio.run(main())
```

---

## Técnicas Implementadas

- **TLS Fingerprinting** — impersonação de fingerprints JA3/JA4 via `curl_cffi`
- **Canvas Fingerprinting** — randomização de ruído no renderizador Canvas 2D
- **WebGL Fingerprinting** — spoofing de vendor/renderer WebGL
- **WebRTC Leak Prevention** — desativação de vazamento de IP real
- **JavaScript Challenges** — bypass de Cloudflare, DataDome e Akamai
- **Simulação Comportamental** — movimentos de mouse em curvas de Bezier, scroll natural, delays humanos
- **Proxy Rotation** — rotação automática com health check e ban de proxies lentos
- **CDP/DevTools Detection** — remoção de flags detectáveis do Chrome DevTools Protocol
- **Rate Limiting Bypass** — distribuição de requisições entre proxies
- **Honeypot Detection** — identificação e exclusão de links armadilha
- **CAPTCHA Resolution** — suporte a 2Captcha e Capsolver com fallback entre serviços
- **Cache Inteligente** — cache SQLite com TTL configurável e desduplicação

---

## Variáveis de Ambiente

- `CAPSOLVER_API_KEY` — Chave de API do Capsolver para resolução de CAPTCHA
- `TWOCAPTCHA_API_KEY` — Chave de API do 2Captcha para resolução de CAPTCHA
- `PROXY_LIST` — Lista de proxies separados por vírgula (formato `protocolo://user:pass@host:porta`)

---

## Créditos

**Autor: Evandro Fonseca Junior**

---

## Licença

Distribuído sob licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais informações.

---

## Referências

COOK, Garrett, et al. *There's a Hole in the Bucket: Large-Scale Analysis of CAPTCHA Abuse*. 2020.

VASTEL, Antoine. *Modern Fingerprinting Techniques: A Survey*. 2017.

LAPERDRIX, Pierre, et al. *Beauty and the Beast: Diverting Modern Web Browsers from Building Honest Fingerprints*. 2016.

ACAR, Gunes, et al. *The Web Never Forgets: Persistent Tracking Mechanisms in the Wild*. 2014.
