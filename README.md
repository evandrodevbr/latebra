# latebra

**Anti-bot MCP server for anonymous web scraping with multi-layer evasion pipeline.**

latebra combines TLS fingerprinting, browser stealth, human behavioral simulation, proxy rotation, and CAPTCHA solving into a single MCP server. Each layer features automatic fallback: if the HTTP request fails due to detection, the pipeline escalates to browser stealth; if the browser is blocked, it attempts extraction via headless crawler -- always preserving maximum anonymity.

---

## Pipeline

```
+----------+    +-----------+    +--------------+
| REQUEST  |--->|  BROWSER  |--->| EXTRACTION   |
| curl_cffi|    | Playwright|    | Crawl4AI     |
| TLS imp. |    | + stealth |    | + regex      |
+----+-----+    +-----+-----+    +------+-------+
     |                |                 |
     v                v                 v
+----------+    +-----------+    +--------------+
|  PROXY   |    |STEALTH    |    |   CACHE      |
| Manager  |    |Fingerprint|    |  SQLite TTL  |
| Rotation |    | + Behavior|    |  Dedup       |
| Health   |    | Canvas    |    |              |
| Check    |    | WebGL     |    |              |
+----------+    +-----------+    +--------------+
                     |
                     v
               +----------+
               |  CAPTCHA  |
               |  Solver   |
               | 2Captcha  |
               | Capsolver |
               +----------+
```

The pipeline follows a graceful degradation strategy:

1. **Request** -- initial attempt with `curl_cffi` and TLS impersonation
2. **Browser** -- if detected, launches Playwright with stealth profile
3. **Extraction** -- extracts content with Crawl4AI or regex fallback
4. **Cache** -- results stored in SQLite with configurable TTL

Auxiliary modules (proxy, stealth, captcha) operate across all layers.

---

## Architecture

```
src/latebra/
|
+-- server.py                # MCP server -- tools: scrape, extract, health
|
+-- pipeline.py              # SmartScrapePipeline -- fallback orchestrator
|
+-- layers/
|   +-- request.py           # curl_cffi + TLS impersonation + proxy
|   +-- browser.py           # Playwright + stealth initialization
|   +-- extraction.py        # Crawl4AI + regex fallback + SQLite TTL cache
|
+-- proxy/
|   +-- manager.py           # Proxy rotation, health check, automatic ban
|
+-- stealth/
|   +-- fingerprint.py       # Canvas, WebGL, WebRTC spoofing
|   +-- behavior.py          # Bezier curves, human delays, natural scroll
|
+-- captcha/
    +-- solver.py            # 2Captcha + Capsolver
```

### Execution Flow

```
                  +-------------------+
                  |  MCP Client       |
                  |  (Claude, Cursor) |
                  +--------+----------+
                           |
                           v
                  +-------------------+
                  |  server.py        |
                  |  scrape / extract |
                  +--------+----------+
                           |
                           v
                  +-------------------+
                  |  pipeline.py      |
                  |  fallback chain   |
                  +---+---+---+-------+
                      |   |   |
              +-------+   |   +-------+
              v           v           v
        +----------+ +--------+ +----------+
        | request  | |browser | |extraction|
        | curl_cffi| |Playwr. | |Crawl4AI  |
        | TLS imp. | |stealth | |+ regex   |
        +----------+ +--------+ +----------+
              |           |           |
              +-----------+-----------+
                          |
                          v
                  +-------------------+
                  |   SQLite Cache    |
                  |   (TTL + dedup)   |
                  +-------------------+
```

---

## Installation

Python 3.12+ is required for pip and uv installation methods.

### npm (recommended)

The npm package wraps the Python server and auto-installs all dependencies:

```bash
npm install -g latebra
```

### uv

```bash
git clone https://github.com/evandrodevbr/latebra.git
cd latebra
uv sync
```

### pip

```bash
git clone https://github.com/evandrodevbr/latebra.git
cd latebra

# Minimal (MCP only)
pip install -e .

# With browser support
pip install -e ".[browser]"

# With extraction support
pip install -e ".[extraction]"

# With CAPTCHA support
pip install -e ".[captcha]"

# Complete (all modules)
pip install -e ".[all]"
```

---

## Usage

### As MCP Server

```bash
latebra run
```

Or via Python directly:

```bash
python -m latebra run
```

Configure in your MCP client (Claude Desktop, Cursor, Hermes Agent):

```json
{
  "mcpServers": {
    "latebra": {
      "command": "python",
      "args": ["-m", "latebra", "run"],
      "env": {
        "PROXY_LIST": "socks5://user:pass@proxy1:1080,socks5://user:pass@proxy2:1080",
        "CAPSOLVER_API_KEY": "your_key_here"
      }
    }
  }
}
```

Available tools:

- `scrape` -- intelligent scraping with HTTP to Browser fallback
- `extract` -- direct structured content extraction
- `health` -- status check and anonymity level report

### As Python Library

```python
import asyncio
from latebra.pipeline import SmartScrapePipeline

async def main():
    pipeline = SmartScrapePipeline(
        proxy_list=["socks5://user:pass@proxy1:1080"],
        capsolver_key="your_key",
    )

    result = await pipeline.scrape(
        url="https://example.com",
        force_browser=False,     # tries HTTP first
        extract_structured=True, # extracts with Crawl4AI
    )

    print(f"Status: {result.status}")
    print(f"Content: {result.content[:500]}")
    print(f"Layer used: {result.layer}")

asyncio.run(main())
```

---

## Techniques Implemented

- **TLS Fingerprinting** -- JA3/JA4 fingerprint impersonation via `curl_cffi`
- **Canvas Fingerprinting** -- noise randomization in Canvas 2D renderer
- **WebGL Fingerprinting** -- WebGL vendor/renderer spoofing
- **WebRTC Leak Prevention** -- real IP address leak prevention
- **JavaScript Challenges** -- Cloudflare, DataDome, and Akamai bypass
- **Behavioral Simulation** -- Bezier curve mouse movements, natural scroll, human-like delays
- **Proxy Rotation** -- automatic rotation with health check and slow proxy banning
- **CDP/DevTools Detection** -- removal of detectable Chrome DevTools Protocol flags
- **Rate Limiting Bypass** -- request distribution across multiple proxies
- **Honeypot Detection** -- identification and exclusion of trap links
- **CAPTCHA Resolution** -- 2Captcha and Capsolver support with fallback between services
- **Intelligent Cache** -- SQLite cache with configurable TTL and deduplication

---

## Recommended Services

### Proxy Services

A curated list of cost-effective proxy providers that work well with latebra:

**Webshare** -- Residential proxies with 10 free proxies included, datacenter plans from $2.99/month.
- Link: https://www.webshare.io
- Pricing: Residential from $4.50/GB, datacenter plans from $2.99/month
- Best for: developers and small teams needing a free tier to start

**IPRoyal** -- Pay-as-you-go residential proxies with no monthly commitment, static residential available.
- Link: https://iproyal.com
- Pricing: Residential from $1.75/GB, static residential from $2.40/proxy/month
- Best for: flexible usage without long-term contracts

**Bright Data** -- Largest proxy network with 72M+ IPs, enterprise-grade proxy manager, and best geographic coverage.
- Link: https://brightdata.com
- Pricing: Residential from approximately $5.04/GB
- Best for: enterprise workloads requiring maximum coverage and reliability

**Smartproxy** -- 55M+ IP pool with a well-designed dashboard and browser extensions for simplified setup.
- Link: https://smartproxy.com
- Pricing: Residential from $3/GB
- Best for: teams that value ease of use and dashboard management

**Proxy-Cheap** -- Affordable residential and static residential proxies suitable for small to medium projects.
- Link: https://proxy-cheap.com
- Pricing: Residential from approximately $3/GB
- Best for: budget-conscious projects with moderate volume requirements

### CAPTCHA Solvers

A curated list of cost-effective CAPTCHA solving services that work well with latebra:

**2Captcha** -- Widest CAPTCHA type coverage with proven reliability across reCAPTCHA, hCaptcha, and image captchas.
- Link: https://2captcha.com
- Pricing: reCAPTCHA v2 from $0.50/1000, reCAPTCHA v3 $1-$3/1000
- Best for: general-purpose solving with the broadest feature support

**Capsolver** -- AI-powered auto-solving with support for Cloudflare Turnstile, hCaptcha, and FunCaptcha.
- Link: https://www.capsolver.com
- Pricing: reCAPTCHA v2 approximately $1/1000
- Best for: modern CAPTCHA types including Cloudflare Turnstile

**Anti-Captcha** -- Consistent pricing with good API documentation and a browser extension for assisted solving.
- Link: https://anti-captcha.com
- Pricing: reCAPTCHA v2 $0.50-$2/1000
- Best for: teams that value well-documented APIs and predictable pricing

**CapMonster** -- Competitive pricing for reCAPTCHA v2 with fast solving speeds and a Chrome extension.
- Link: https://capmonster.cloud
- Pricing: Competitive rates for reCAPTCHA v2
- Best for: high-volume operations requiring fast turnaround

**DeathByCaptcha** -- Established service since 2010 with OCR-based image CAPTCHA solving and long-standing reliability.
- Link: https://www.deathbycaptcha.com
- Pricing: reCAPTCHA v2 $1.49/1000
- Best for: projects needing a mature, time-tested provider

Note: These services are third-party recommendations. latebra does not endorse any specific provider. Choose based on your budget, volume, and region requirements. All services listed are optional -- latebra works without proxies or CAPTCHA solvers configured.

---

## Environment Variables

- `CAPSOLVER_API_KEY` -- Capsolver API key for CAPTCHA resolution
- `TWOCAPTCHA_API_KEY` -- 2Captcha API key for CAPTCHA resolution
- `PROXY_LIST` -- Comma-separated proxy list (format: `protocol://user:pass@host:port`)

---

## Credits

**Author: Evandro Fonseca Junior**

---

## License

Distributed under the MIT license. See the [LICENSE](LICENSE) file for details.

---

## References

COOK, Garrett, et al. *There's a Hole in the Bucket: Large-Scale Analysis of CAPTCHA Abuse*. 2020.

VASTEL, Antoine. *Modern Fingerprinting Techniques: A Survey*. 2017.

LAPERDRIX, Pierre, et al. *Beauty and the Beast: Diverting Modern Web Browsers from Building Honest Fingerprints*. 2016.

ACAR, Gunes, et al. *The Web Never Forgets: Persistent Tracking Mechanisms in the Wild*. 2014.
