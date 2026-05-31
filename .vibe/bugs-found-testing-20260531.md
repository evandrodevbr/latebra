# Bugs Encontrados — Teste Real do MCP Latebra

Data: 2026-05-31
Testador: Hermes Agent com deepseek-v4-pro
Ambiente: Linux 6.17.0, Python 3.12, venv latebra v0.2.0

## Resumo Executivo
- **Bugs críticos:** 2 (Camoufox API, Nodriver API — quebram Layer 2 inteira)
- **Bugs altos:** 3 (erro sobrescrito, DNS sem early termination, double fallback)
- **Bugs médios:** 1 (URL validation não integrada)
- **O que funciona:** Layer 1 (curl_cffi), Layer 3 (Crawl4AI), ProxyManager, CaptchaSolver, URL validation
- **113/113 testes passam** — mas coverage é principalmente unitário, sem teste de integração real

---

## BUG 1 [CRÍTICO] — Camoufox v0.4.11 API incompatível
**Arquivo:** `src/latebra/layers/browser.py:116-117`
**Erro:** `'Camoufox' object does not support the asynchronous context manager protocol`
**Causa raiz:** `Camoufox` (de `camoufox.sync_api`) é síncrono. Deveria usar `AsyncCamoufox` (de `camoufox.async_api`) que suporta `async with`.
**Impacto:** Qualquer tentativa de usar o Camoufox falha. Layer 2 efetivamente tem só Patchright funcional.
**API correta:**
```python
from camoufox import AsyncCamoufox
async with AsyncCamoufox(headless=True) as browser:
    page = await browser.new_page()
```

## BUG 2 [CRÍTICO] — Nodriver v0.50.3 API incompatível
**Arquivo:** `src/latebra/layers/browser.py:130`
**Erro:** `module 'nodriver' has no attribute 'By'`
**Causa raiz:** `nd.By` foi removido do nodriver v0.50+. A API nova usa `page.wait_for(selector, timeout)` ou `page.select(selector, timeout)`.
**Impacto:** Qualquer tentativa de usar nodriver falha.
**API correta:**
```python
import nodriver as nd
browser = await nd.start(headless=True)
page = await browser.get(url)
await page.wait_for("body", timeout=15)  # ou page.select("body", timeout=15)
await page.sleep(1)
html = await page.get_content()
browser.stop()
```

## BUG 3 [ALTO] — Mensagem de erro sobrescrita no pipeline
**Arquivo:** `src/latebra/pipeline.py:125-143`
**Comportamento:** Quando a camada request falha com `ERR_NAME_NOT_RESOLVED`, as camadas browser tentam e falham também, sobrescrevendo `result.error` com erros menos úteis do browser (ex: `module 'nodriver' has no attribute 'By'`).
**Causa raiz:** O pipeline armazena `last_error` de cada tentativa de browser, e retorna `last_error or req_result.error` — mas `last_error` SEMPRE existe porque todos os browsers falham. O erro real (DNS) é mascarado.
**Correção:** Coletar erros em lista e priorizar o erro da camada correspondente ao sucesso mais próximo. Ou parar browser antes para erros terminais (ver BUG 4).

## BUG 4 [ALTO] — Sem early termination para erros de rede
**Arquivo:** `src/latebra/pipeline.py:123-134`
**Comportamento:** Quando `curl_cffi` falha com erro de DNS (`net::ERR_NAME_NOT_RESOLVED`), o pipeline tenta TODOS os browsers (Patchright, Camoufox, Nodriver) que também falham com DNS.
**Causa raiz:** Não há verificação se o erro da camada 1 é terminal (irrecuperável em qualquer camada) antes de tentar fallback.
**Correção:** Adicionar check de erros terminais (DNS, connection refused, timeout) antes de tentar Layer 2. Se for terminal, retornar erro imediatamente.

## BUG 5 [ALTO] — Double fallback: pipeline + browser layer iteram engines
**Arquivos:** `src/latebra/pipeline.py:124-134` e `src/latebra/layers/browser.py:62-84`
**Comportamento:** O pipeline itera `["patchright", "camoufox", "nodriver"]` chamando `browser_layer.scrape(url, engine=engine)` para cada um. MAS `browser_layer.scrape()` já contém seu próprio loop de fallback interno. Resultado: browsers são tentados mais vezes que necessário.
- pipeline chama scrape(patchright) → browser tenta [patchright, camoufox, nodriver]
- pipeline chama scrape(camoufox) → browser tenta [camoufox, nodriver]  
- pipeline chama scrape(nodriver) → browser tenta [nodriver]
Total: patchright 1x, camoufox 2x, nodriver 3x (para um erro terminal de DNS!)
**Causa raiz:** Duas camadas de fallback sem coordenação. 
**Correção (2 opções):**
- A) Remover iteração do pipeline: chamar `browser_layer.scrape(url)` uma vez sem engine específica, deixar browser gerenciar seu próprio fallback.
- B) Remover fallback do browser: `browser_layer.scrape()` tenta apenas o engine especificado, sem fallback interno.

Recomendação: **Opção A** — cada camada gerencia seu próprio fallback. O pipeline coordena entre camadas (request → browser → extraction), e cada camada gerencia seus próprios backends.

## BUG 6 [MÉDIO] — URL validation não integrada ao pipeline
**Arquivos:** `src/latebra/pipeline.py:99`, `src/latebra/server.py:102`
**Comportamento:** O módulo `validation.py` com proteção SSRF existe e funciona, mas nunca é chamado antes de fazer requests. O servidor chama `pipeline.scrape(url)` diretamente sem validar.
**Causa raiz:** Validação implementada mas não integrada ao fluxo principal.
**Correção:** Chamar `validation.validate(url)` em `pipeline.scrape()`, `scrape_with_browser()`, e `check_anonymity()`.

---

## O Que Funciona (sem bugs)
- ✅ Layer 1 (curl_cffi) — TLS impersonation, retry, fallback para httpx
- ✅ Layer 3 (Crawl4AI extraction) — cache, título, links, fallback HTMLParser
- ✅ ProxyManager — circuit breaker, rotation strategies
- ✅ CaptchaSolver — 2captcha/capsolver com polling e tratamento de erros
- ✅ URL Validation (SSRF) — bloqueia localhost, RFC1918, AWS metadata
- ✅ MCP server — stdio protocol, 3 tools registradas
- ✅ 113/113 testes unitários passando
