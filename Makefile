# ┌──────────────────────────────────────────────────┐
# │  latebra — Makefile para desenvolvimento          │
# │  Autor: Evandro Fonseca Junior                   │
# │  Licença: MIT                                    │
# └──────────────────────────────────────────────────┘

.PHONY: help install install-dev test test-cov lint format clean build publish

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

# ── Default ──────────────────────────────────────
help: ## Exibe esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────
$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip --quiet

install: $(VENV)/bin/activate ## Instala latebra + dependências
	$(PIP) install -e ".[all]" --quiet
	@echo "✓ latebra instalado no modo editável"

install-dev: install ## Instala + dependências de dev
	$(PIP) install -e ".[dev]" --quiet
	@echo "✓ Ferramentas de dev instaladas"

# ── Tests ────────────────────────────────────────
test: install-dev ## Roda todos os testes
	$(PYTEST) tests/ -v --tb=short

test-cov: install-dev ## Roda testes com cobertura
	$(PYTEST) tests/ -v --tb=short \
		--cov=src/latebra \
		--cov-report=term-missing \
		--cov-report=html

test-unit: install-dev ## Roda apenas testes unitários
	$(PYTEST) tests/ -v -m "unit" --tb=short

test-slow: install-dev ## Roda apenas testes lentos
	$(PYTEST) tests/ -v -m "slow" --tb=short

# ── Lint & Format ────────────────────────────────
lint: install-dev ## Verifica estilo e tipos
	$(RUFF) check src/ tests/
	$(MYPY) src/

format: install-dev ## Formata código automaticamente
	$(RUFF) check src/ tests/ --fix
	$(RUFF) format src/ tests/

# ── Clean ────────────────────────────────────────
clean: ## Remove artefatos de build
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .mypy_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Limpo"

clean-all: clean ## Remove venv + cache
	rm -rf $(VENV)
	rm -rf ~/.cache/latebra/
	@echo "✓ Tudo limpo"

# ── Build & Publish ──────────────────────────────
build: clean ## Cria pacote wheel
	$(PIP) install build --quiet
	$(PYTHON) -m build --wheel
	@echo "✓ Pacote criado em dist/"

publish: build ## Publica no PyPI (requer token)
	$(PIP) install twine --quiet
	$(PYTHON) -m twine upload dist/*
	@echo "✓ Publicado no PyPI"

# ── Run ──────────────────────────────────────────
run: install ## Inicia o servidor MCP
	$(PYTHON) -m latebra.server

run-verbose: install ## Inicia com logging DEBUG
	LATEBRA_LOG_LEVEL=DEBUG $(PYTHON) -m latebra.server

# ── Docker ───────────────────────────────────────
docker-build: ## Constrói imagem Docker
	docker build -t latebra:latest .

docker-run: ## Roda servidor MCP no Docker
	docker run -i --rm \
		-e LATEBRA_PROXIES="$${LATEBRA_PROXIES:-}" \
		-e LATEBRA_2CAPTCHA_KEY="$${LATEBRA_2CAPTCHA_KEY:-}" \
		latebra:latest
