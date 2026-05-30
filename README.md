# latebra 🕵️‍♂️

**MCP anti-bot web scraping com máxima anonimidade.**

Pipeline multi-camadas que evita detecção combinando TLS fingerprinting, browser stealth, simulação comportamental e proxy rotation.

## Pipeline

```
curl_cffi (HTTP) → Patchright (Browser) → Camoufox (Firefox) → [CAPTCHA solver] → [Proxy rotation]
```

## Instalação

```bash
pip install latebra
# ou com suporte a todos os browsers
pip install "latebra[all]"
```

## Uso (MCP)

```bash
python -m latebra run
```

Conecte como MCP client e use as ferramentas:

- `latebra_scrape` — scrape inteligente (HTTP → Browser)
- `latebra_scrape_with_browser` — força browser
- `latebra_check_anonymity` — testa nível de anonimidade

## Arquitetura

```
┌────────────────────────────────────────────────────────────┐
│                    latebra MCP Server                       │
├────────────────────────────────────────────────────────────┤
│  Layer 1: curl_cffi  (TLS impersonation + proxies)        │
│  Layer 2: Patchright  (CDP stealth + fingerprints)        │
│  Layer 3: Camoufox   (Firefox stealth)                    │
│  Layer 4: nodriver   (last resort)                        │
│  Layer 5: Crawl4AI   (extraction + dedup)                 │
└────────────────────────────────────────────────────────────┘
```

## Técnicas Implementadas

- TLS Fingerprinting (JA3/JA4) via curl_cffi
- Browser Fingerprinting (Canvas, WebGL, AudioContext) randomizado
- JavaScript Challenges (Cloudflare, DataDome) bypass
- Behavioral Analysis (mouse, scroll, timing simulation)
- IP Reputation (proxy rotation)
- CDP/DevTools Detection (flags removidas)
- Rate Limiting e Honeypots

## Licença

MIT
