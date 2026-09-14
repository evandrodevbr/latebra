# latebra

**Servidor MCP para web scraping anti-bot: pipeline de evasão em camadas (TLS impersonation, browsers stealth, extração) rodando 100% local, exposto como ferramentas MCP para agentes de IA.**

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.x-green.svg)](https://modelcontextprotocol.io)
[![Testes](https://img.shields.io/badge/testes-163%20passaram%20de%20166-brightgreen.svg)](https://github.com/evandrodevbr/latebra/tree/master/tests)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-purple.svg)](LICENSE)

## Sobre

Fazer scraping de sites protegidos por sistemas anti-bot (Cloudflare, DataDome, Akamai e similares) normalmente significa pagar uma API de scraping em nuvem ou montar na mão uma pilha de browser com stealth. O latebra junta os dois caminhos em um único servidor MCP local: um cliente MCP (Claude, Cursor, Hermes, qualquer agente compatível) chama ferramentas como `latebra_scrape` ou `latebra_search`, e o servidor decide por requisição se basta uma requisição HTTP com TLS impersonation ou se é preciso um browser stealth.

O que ele faz:

- expõe 8 ferramentas MCP via stdio (scrape, scrape com browser, batch, crawl, busca, interação, checagem de anonimato e caminho dos logs);
- sobe a pipeline automaticamente: requisição `curl_cffi` com fingerprint TLS de Chrome e, em caso de bloqueio, browsers Patchright, Camoufox ou nodriver;
- extrai e cacheia conteúdo (Crawl4AI quando instalado, extração nativa caso contrário, cache SQLite com TTL);
- busca na web via SearXNG local quando disponível, com fallback para DuckDuckGo, Google e Bing pela biblioteca `ddgs`;
- suporta rotação de proxies com circuit breaker, simulação comportamental e resolução de CAPTCHA via 2Captcha/Capsolver.

Tudo roda localmente. Não há dependência de nuvem nem conta em serviço externo.

## Como funciona

```
Cliente MCP (JSON-RPC via stdio)
        |
        v
server.py            LatebraServer, 8 ferramentas, despacho por nome
        |
        v
SmartScrapePipeline  decisão por URL, fallback camada a camada
        |
        +-- Camada 1: AsyncRequestLayer (curl_cffi, impersonation de Chrome)
        |       sucesso -> extração + cache SQLite
        |       falha -> erro de rede terminal? para : Camada 2
        |
        +-- Camada 2: AsyncBrowserLayer (Patchright -> Camoufox -> nodriver)
        |       sucesso -> extração
        |
        +-- Camada 3: AsyncExtractionLayer (cache -> Crawl4AI -> nativa)
        |
        +-- Apoio: ProxyManager (rotação + circuit breaker),
                   stealth de fingerprint/comportamento, CaptchaSolver
```

A busca tem caminho próprio em duas etapas: o `SearchLayer` testa o SearXNG em `http://localhost:8090`; se responder, a consulta vai para lá, senão cai nos motores nativos (`BuiltInSearchLayer` sobre `ddgs`). A variável `LATEBRA_SEARCH_BACKEND` força `auto` (padrão), `searxng` ou `built-in`.

## Stack

| Camada | Escolha |
|---|---|
| Runtime | Python 3.12+, assíncrono de ponta a ponta |
| MCP | SDK `mcp` 1.x (servidor stdio) |
| HTTP / TLS | `curl_cffi` com perfis de impersonation do Chrome |
| Browsers (opcional) | Patchright, Camoufox, nodriver |
| Extração (opcional) | Crawl4AI e extração nativa |
| Busca | SearXNG (opcional) ou `ddgs` (DuckDuckGo, Google, Bing) |
| Cache | SQLite com TTL (`~/.cache/latebra`) |
| Testes / ferramentas | pytest, pytest-asyncio, ruff, mypy |
| Empacotamento | setuptools, lockfile `uv`, console scripts `latebra` e `latebra-mcp` |

## Requisitos

- Python 3.12 ou superior (verificado no 3.12.14)
- `uv` (recomendado) ou `pip`
- Acesso à internet para scraping real
- Opcional: Docker (para o SearXNG), proxies, chaves da 2Captcha/Capsolver
- Para o modo browser: Chrome/Chromium instalado (o nodriver usa o do sistema) ou os browsers stealth baixados pelo `latebra install`

## Início rápido

```bash
git clone https://github.com/evandrodevbr/latebra.git
cd latebra

# Ambiente virtual + instalação (núcleo + ferramentas de teste)
uv venv .venv --python 3.12
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Sobe o servidor MCP via stdio
python -m latebra run
```

`uvx latebra` ainda **não funciona**: o pacote não está publicado no PyPI. Instale a partir do repositório.

Para a instalação completa (browsers + extração Crawl4AI):

```bash
uv pip install -e ".[all,dev]"
latebra install                  # baixa Chromium do Patchright e binários do Camoufox
```

O caminho com `pip` funciona igual: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[all,dev]"`.

### Configuração no cliente MCP

Exemplo para qualquer cliente MCP que aceite comando e argumentos (ajuste o caminho do venv):

```json
{
  "mcpServers": {
    "latebra": {
      "command": "/caminho/para/latebra/.venv/bin/python",
      "args": ["-m", "latebra", "run"]
    }
  }
}
```

Ou use o console script instalado pelo wheel: `latebra-mcp` (mesmo servidor stdio).

Há instaladores avulsos: `install.sh` (Linux/macOS) e `install.ps1` (Windows). Ambos clonam a branch `master` em `~/.latebra` (ajustável com `LATEBRA_HOME`), criam o venv, instalam `.[all]` e registram o servidor no config do Claude Desktop quando ele existe.

## Ferramentas MCP

Verificadas com um handshake real de `initialize` + `tools/list` contra o wheel empacotado; o servidor reporta exatamente estas 8 ferramentas:

| Ferramenta | O que faz | Parâmetros |
|---|---|---|
| `latebra_scrape` | Executa a pipeline multi-camada para uma URL (requisição primeiro, browser como fallback). | `url` (obrigatório) |
| `latebra_scrape_with_browser` | Pula a camada de requisição e usa um browser direto. | `url` (obrigatório), `browser` = `patchright` \| `camoufox` \| `nodriver` (padrão `patchright`) |
| `latebra_batch_scrape` | Scraping de várias URLs em paralelo com limite de concorrência. | `urls` (obrigatório), `max_concurrent` (padrão 5) |
| `latebra_crawl` | Crawl em largura a partir de uma URL semente, seguindo links. | `url` (obrigatório), `max_depth` (padrão efetivo 2), `max_pages` (padrão efetivo 20) |
| `latebra_search` | Busca web via SearXNG ou motores nativos. | `query` (obrigatório), `max_results` (padrão 10) |
| `latebra_interact` | Controla a página do browser: navegar, clicar, digitar. | `action` = `navigate` \| `click` \| `type` (obrigatório), `url`, `selector`, `text` |
| `latebra_check_anonymity` | Raspa uma página de detecção e reporta os marcadores de bot encontrados na resposta. | `url` (padrão `https://httpbin.org/headers`) |
| `latebra_get_log_path` | Retorna o caminho absoluto do diretório de logs (para relatar problemas). | nenhum |

As respostas são JSON. O `latebra_scrape` reporta `status`, `layer_used` (`request` ou `browser_*`), `content_length`, `timing_ms`, `title` e um preview do conteúdo.

As ferramentas de browser exigem o extra `[browser]` e um binário de browser; sem isso a pipeline registra o erro da camada e retorna `status: "error"` em vez de quebrar.

## CLI

```bash
latebra --version        # latebra 0.2.0
latebra run              # inicia o servidor MCP (comando padrão)
latebra install          # pós-instalação: Chromium do Patchright + binários do Camoufox
```

## Produção

Gere o wheel e rode como artefato instalado:

```bash
uv build                                   # -> dist/latebra-0.2.0-py3-none-any.whl (+ sdist)
uv venv /opt/latebra/.venv --python 3.12
uv pip install --python /opt/latebra/.venv/bin/python dist/latebra-0.2.0-py3-none-any.whl
/opt/latebra/.venv/bin/python -m latebra run   # ou: latebra-mcp
```

A instalação do wheel foi verificada de ponta a ponta: venv novo, instalação do wheel, handshake `initialize` + `tools/list` retornando as 8 ferramentas e `latebra_get_log_path` respondendo.

Notas de operação:

- o processo fala JSON-RPC em stdin/stdout, feito para ser iniciado pelo cliente MCP, não como daemon;
- logs ficam em `~/.local/share/latebra/logs` (com rotação; caminho também via `latebra_get_log_path`);
- o cache SQLite fica em `~/.cache/latebra`;
- não há imagem Docker publicada nem Dockerfile no repositório;
- não há release no PyPI ainda; distribua o wheel ou instale a partir do código.

## Estrutura do projeto

```
src/latebra/
├── server.py          servidor MCP: 8 definições de ferramentas + despacho
├── pipeline.py        SmartScrapePipeline: decisão por URL
├── config.py          LatebraConfig.from_env (variáveis LATEBRA_*)
├── constants.py       limites, user agents, fingerprints, timeouts
├── layers/
│   ├── request.py     camada HTTP com curl_cffi
│   ├── browser.py     camada Patchright / Camoufox / nodriver
│   ├── extraction.py  cache SQLite + extração
│   ├── crawler.py     crawler BFS
│   ├── interact.py    navigate / click / type
│   ├── search.py      SearXNG com detecção automática e fallback
│   └── search_builtin.py  motores DuckDuckGo / Google / Bing (ddgs)
├── proxy/manager.py   rotação + circuit breaker
├── stealth/           randomização de fingerprint e comportamento
├── captcha/solver.py  clientes 2Captcha / Capsolver
├── validation.py      validação de URL contra SSRF (bloqueia faixas privadas)
├── log_utils.py       logs em arquivo com rotação
└── install.py         pós-instalação do `latebra install`
tests/                 suítes unitária, de camadas e de performance (183 testes coletados)
docs/                  SDD, baseline de performance, planos e specs
```

## Verificação

Números medidos em 2026-09-14 (Manjaro Linux, Python 3.12.14, repositório em `1f9409e`, `mcp` 1.30.0):

| Checagem | Comando | Resultado |
|---|---|---|
| Import e CLI | `latebra --version` | `latebra 0.2.0` |
| Handshake MCP | `initialize` + `tools/list` + `latebra_get_log_path` via stdio | OK, 8 ferramentas, chamada respondida |
| Subconjunto offline | `pytest tests/ -m "not slow" --ignore=tests/performance --ignore=tests/test_search_builtin.py --ignore=tests/test_p0_features.py --ignore=tests/test_layers_search.py` | 113 passaram em 0.92s |
| Suíte completa | `pytest tests/ -m "not slow"` | 166 selecionados (183 coletados, 17 lentos deselecionados): 163 passaram, 2 falharam, 1 pulado |
| Build do wheel | `uv build` | `dist/latebra-0.2.0-py3-none-any.whl` gerado e instalado em venv novo |
| Fallback de browser | testes de batch com páginas pequenas | nodriver dirigiu o Chrome do sistema com sucesso |
| Lint | `ruff check src/ tests/` | 116 avisos (aberto) |
| Tipos | `mypy src/` | 45 erros em modo strict (aberto) |

Os 2 testes que falharam dependem de buscadores externos: `test_google_engine_returns_results` (o Google não devolveu resultados na rede auditada) e `test_search_latency` (9,5s e 22s medidos contra o limite de 5s, com engines expirando). O teste pulado precisa de um SearXNG rodando em `localhost:8090` (serviço opcional) e se auto-pula quando ausente. Todo o resto passou, incluindo as suítes de crawl, batch, fallback de browser e stealth.

## Estado atual e limitações

- Sem CI configurada e sem release no PyPI: `uvx latebra` e `pip install latebra` não funcionam; instale do código ou do wheel gerado.
- A suíte de testes não é hermética. Testes de busca chamam buscadores reais (falham sob rate limit, como observado na auditoria), e os de crawl/batch chamam `httpbin.org`.
- O `config.py` lê todo o conjunto `LATEBRA_*`, mas o servidor só conecta `LATEBRA_PROXIES`, `LATEBRA_2CAPTCHA_KEY`, `LATEBRA_CAPSOLVER_KEY` e `LATEBRA_SEARCH_BACKEND`. As configurações de cache, stealth e timeout são lidas mas ainda não aplicadas na pipeline.
- A URL do SearXNG é um padrão fixo (`http://localhost:8090`); não há variável de ambiente para ela, apenas o argumento de construtor `LatebraServer(searxng_url=...)`.
- O `mcp` está fixado em `>=1.0.0,<2.0.0`: o SDK 2.x removeu a API de servidor `list_tools`/`call_tool` usada aqui, então a 1.x é obrigatória até a migração.
- Patchright e Camoufox precisam dos binários baixados pelo `latebra install`; só o nodriver funciona com o Chrome do sistema.
- Dívida de lint e tipos em aberto (116 achados do ruff, 45 erros do mypy strict); nada bloqueia a execução.
- Os instaladores `install.sh` / `install.ps1` existem mas não foram executados nesta auditoria (instalam em `~/.latebra` e editam o config do Claude Desktop).
- As traduções em outros idiomas (`README.es.md`, `README.ja.md`, `README.zh.md`) existem e podem estar defasadas em relação a este documento.

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/SDD.md`](docs/SDD.md) | Plano spec-driven e componentes |
| [`docs/PERFORMANCE_BASELINE.md`](docs/PERFORMANCE_BASELINE.md) | Baseline de performance (2026-05-31) |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | Planos de implementação (logging, backend de busca) |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Especificações de design |
| [`AGENTS.md`](AGENTS.md) | Notas de estrutura para agentes de código |

## Licença

MIT, veja [`LICENSE`](LICENSE). Copyright (c) 2026 Evandro Fonseca Junior.
