# latebra

**Servidor MCP anti-bot para web scraping anónimo con pipeline de evasión multicapa.**

latebra combina suplantación de huellas TLS, navegador oculto, simulación de comportamiento humano, rotación de proxies y resolución de CAPTCHAs en un único servidor MCP. Cada capa cuenta con degradación automática: si la solicitud HTTP falla por detección, el pipeline escala a navegador oculto; si el navegador es bloqueado, intenta extracción mediante crawler sin interfaz gráfica -- preservando siempre el máximo anonimato.

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

El pipeline sigue una estrategia de degradación gradual:

1. **Request** -- intento inicial con `curl_cffi` y suplantación TLS
2. **Browser** -- si es detectado, lanza Playwright con perfil oculto
3. **Extraction** -- extrae contenido con Crawl4AI o con expresiones regulares como alternativa
4. **Cache** -- resultados almacenados en SQLite con TTL configurable

Los módulos auxiliares (proxy, stealth, captcha) operan en todas las capas.

---

## Arquitectura

```
src/latebra/
|
+-- server.py                # Servidor MCP -- herramientas: scrape, extract, health
|
+-- pipeline.py              # SmartScrapePipeline -- orquestador de degradación
|
+-- layers/
|   +-- request.py           # curl_cffi + suplantación TLS + proxy
|   +-- browser.py           # Playwright + inicialización oculta
|   +-- extraction.py        # Crawl4AI + regex alternativo + caché SQLite con TTL
|
+-- proxy/
|   +-- manager.py           # Rotación de proxies, verificación de salud, bloqueo automático
|
+-- stealth/
|   +-- fingerprint.py       # Suplantación de Canvas, WebGL y WebRTC
|   +-- behavior.py          # Curvas de Bezier, pausas humanas, desplazamiento natural
|
+-- captcha/
    +-- solver.py            # 2Captcha + Capsolver
```

### Flujo de Ejecución

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

## Instalación

Se requiere Python 3.12+ para los métodos de instalación vía pip y uv.

### npm (recomendado)

El paquete npm envuelve el servidor Python e instala automáticamente todas las dependencias:

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

# Mínimo (solo MCP)
pip install -e .

# Con soporte de navegador
pip install -e ".[browser]"

# Con soporte de extracción
pip install -e ".[extraction]"

# Con soporte de CAPTCHA
pip install -e ".[captcha]"

# Completo (todos los módulos)
pip install -e ".[all]"
```

---

## Uso

### Como Servidor MCP

```bash
latebra run
```

O directamente vía Python:

```bash
python -m latebra run
```

Configure en su cliente MCP (Claude Desktop, Cursor, Hermes Agent):

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

Herramientas disponibles:

- `scrape` -- scraping inteligente con degradación de HTTP a navegador
- `extract` -- extracción directa de contenido estructurado
- `health` -- verificación de estado e informe de nivel de anonimato

### Como Biblioteca Python

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
        force_browser=False,     # intenta HTTP primero
        extract_structured=True, # extrae con Crawl4AI
    )

    print(f"Status: {result.status}")
    print(f"Content: {result.content[:500]}")
    print(f"Layer used: {result.layer}")

asyncio.run(main())
```

---

## Técnicas Implementadas

- **Suplantación de Huella TLS** -- suplantación de huellas JA3/JA4 vía `curl_cffi`
- **Suplantación de Canvas** -- aleatorización de ruido en el renderizador Canvas 2D
- **Suplantación de WebGL** -- suplantación de proveedor/renderizador WebGL
- **Prevención de Fugas WebRTC** -- prevención de fuga de dirección IP real
- **Desafíos de JavaScript** -- evasión de Cloudflare, DataDome y Akamai
- **Simulación de Comportamiento** -- movimientos de ratón con curvas de Bezier, desplazamiento natural, pausas similares a las humanas
- **Rotación de Proxies** -- rotación automática con verificación de salud y bloqueo de proxies lentos
- **Detección de CDP/DevTools** -- eliminación de indicadores detectables del protocolo Chrome DevTools
- **Evasión de Limitación de Tasa** -- distribución de solicitudes entre múltiples proxies
- **Detección de Honeypots** -- identificación y exclusión de enlaces trampa
- **Resolución de CAPTCHAs** -- soporte para 2Captcha y Capsolver con degradación entre servicios
- **Caché Inteligente** -- caché SQLite con TTL configurable y deduplicación

---

## Servicios Recomendados

### Servicios de Proxy

Una lista seleccionada de proveedores de proxy económicos que funcionan bien con latebra:

**Webshare** -- Proxies residenciales con 10 proxies gratuitos incluidos, planes de centro de datos desde $2.99/mes.
- Enlace: https://www.webshare.io
- Precios: Residencial desde $4.50/GB, planes de centro de datos desde $2.99/mes
- Ideal para: desarrolladores y equipos pequeños que necesitan un nivel gratuito para comenzar

**IPRoyal** -- Proxies residenciales de pago por uso sin compromiso mensual, con proxies residenciales estáticos disponibles.
- Enlace: https://iproyal.com
- Precios: Residencial desde $1.75/GB, residencial estático desde $2.40/proxy/mes
- Ideal para: uso flexible sin contratos a largo plazo

**Bright Data** -- La mayor red de proxies con más de 72M de IPs, gestor de proxies de nivel empresarial y la mejor cobertura geográfica.
- Enlace: https://brightdata.com
- Precios: Residencial desde aproximadamente $5.04/GB
- Ideal para: cargas de trabajo empresariales que requieren máxima cobertura y fiabilidad

**Smartproxy** -- Pool de más de 55M de IPs con un panel de control bien diseñado y extensiones de navegador para una configuración simplificada.
- Enlace: https://smartproxy.com
- Precios: Residencial desde $3/GB
- Ideal para: equipos que valoran la facilidad de uso y la gestión mediante panel de control

**Proxy-Cheap** -- Proxies residenciales y residenciales estáticos asequibles adecuados para proyectos pequeños y medianos.
- Enlace: https://proxy-cheap.com
- Precios: Residencial desde aproximadamente $3/GB
- Ideal para: proyectos con presupuesto limitado y requisitos de volumen moderados

### Solucionadores de CAPTCHA

Una lista seleccionada de servicios de resolución de CAPTCHAs económicos que funcionan bien con latebra:

**2Captcha** -- La cobertura más amplia de tipos de CAPTCHA con fiabilidad comprobada en reCAPTCHA, hCaptcha y CAPTCHAs de imagen.
- Enlace: https://2captcha.com
- Precios: reCAPTCHA v2 desde $0.50/1000, reCAPTCHA v3 $1-$3/1000
- Ideal para: resolución de propósito general con el soporte de funcionalidades más amplio

**Capsolver** -- Resolución automática impulsada por IA con soporte para Cloudflare Turnstile, hCaptcha y FunCaptcha.
- Enlace: https://www.capsolver.com
- Precios: reCAPTCHA v2 aproximadamente $1/1000
- Ideal para: tipos de CAPTCHA modernos, incluido Cloudflare Turnstile

**Anti-Captcha** -- Precios consistentes con buena documentación de API y una extensión de navegador para resolución asistida.
- Enlace: https://anti-captcha.com
- Precios: reCAPTCHA v2 $0.50-$2/1000
- Ideal para: equipos que valoran APIs bien documentadas y precios predecibles

**CapMonster** -- Precios competitivos para reCAPTCHA v2 con velocidades de resolución rápidas y una extensión de Chrome.
- Enlace: https://capmonster.cloud
- Precios: Tarifas competitivas para reCAPTCHA v2
- Ideal para: operaciones de alto volumen que requieren resolución rápida

**DeathByCaptcha** -- Servicio establecido desde 2010 con resolución de CAPTCHAs de imagen basada en OCR y fiabilidad de larga trayectoria.
- Enlace: https://www.deathbycaptcha.com
- Precios: reCAPTCHA v2 $1.49/1000
- Ideal para: proyectos que necesitan un proveedor maduro y probado en el tiempo

Nota: Estos servicios son recomendaciones de terceros. latebra no respalda ningún proveedor específico. Elija según su presupuesto, volumen y requisitos regionales. Todos los servicios listados son opcionales -- latebra funciona sin proxies ni solucionadores de CAPTCHA configurados.

---

## Variables de Entorno

- `CAPSOLVER_API_KEY` -- Clave API de Capsolver para resolución de CAPTCHAs
- `TWOCAPTCHA_API_KEY` -- Clave API de 2Captcha para resolución de CAPTCHAs
- `PROXY_LIST` -- Lista de proxies separada por comas (formato: `protocolo://usuario:contraseña@host:puerto`)

---

## Créditos

**Autor: Evandro Fonseca Junior**

---

## Licencia

Distribuido bajo la licencia MIT. Consulte el archivo [LICENSE](LICENSE) para más detalles.

---

## Referencias

COOK, Garrett, et al. *There's a Hole in the Bucket: Large-Scale Analysis of CAPTCHA Abuse*. 2020.

VASTEL, Antoine. *Modern Fingerprinting Techniques: A Survey*. 2017.

LAPERDRIX, Pierre, et al. *Beauty and the Beast: Diverting Modern Web Browsers from Building Honest Fingerprints*. 2016.

ACAR, Gunes, et al. *The Web Never Forgets: Persistent Tracking Mechanisms in the Wild*. 2014.
