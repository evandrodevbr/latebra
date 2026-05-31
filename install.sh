#!/usr/bin/env bash
# ┌─────────────────────────────────────────────────────┐
# │  latebra v0.2.0 — Single-Command Linux Installer    │
# │  curl -fsSL https://latebra.evandro.app/install.sh | bash  │
# │  Autor: Evandro Fonseca Junior                      │
# │  Licença: MIT                                       │
# └─────────────────────────────────────────────────────┘
set -euo pipefail

# ── Cores ────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${CYAN}→${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*"; exit 1; }

# ── Banner ───────────────────────────────────────
echo ""
echo -e "${BOLD}╔════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      🕶️  latebra anti-bot MCP installer    ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════╝${NC}"
echo ""

# ── Config ──────────────────────────────────────
VERSION="${LATEBRA_VERSION:-0.2.0}"
INSTALL_DIR="${LATEBRA_HOME:-$HOME/.latebra}"
VENV_DIR="$INSTALL_DIR/venv"
REPO_URL="${LATEBRA_REPO:-https://github.com/evandrofjs/latebra.git}"

# ── Pre-flight checks ───────────────────────────
info "Verificando requisitos..."

command -v python3 >/dev/null 2>&1 || err "Python 3 não encontrado. Instale: sudo apt install python3 python3-pip python3-venv"
command -v git >/dev/null 2>&1 || err "Git não encontrado. Instale: sudo apt install git"

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]; }; then
    err "Python 3.12+ é necessário (atual: $PYTHON_VERSION). Instale via deadsnakes PPA ou pyenv."
fi

ok "Python $PYTHON_VERSION encontrado"

# ── Criar diretório ─────────────────────────────
mkdir -p "$INSTALL_DIR"

# ── Virtual environment ─────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "Criando ambiente virtual em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    ok "Ambiente virtual criado"
else
    info "Ambiente virtual existente em $VENV_DIR"
fi

# ── Ativar venv ─────────────────────────────────
source "$VENV_DIR/bin/activate"

# ── Instalar latebra ────────────────────────────
if [ -f "$INSTALL_DIR/pyproject.toml" ]; then
    info "Repositório existente, atualizando via git pull..."
    cd "$INSTALL_DIR"
    git pull --ff-only origin main 2>/dev/null || true
else
    info "Clonando latebra v$VERSION..."
    git clone --branch main "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || \
    info "Repo não disponível, instalando via pip..."
fi

if [ -f "$INSTALL_DIR/pyproject.toml" ]; then
    cd "$INSTALL_DIR"
    info "Instalando latebra (modo editável)..."
    pip install --upgrade pip --quiet
    pip install -e ".[all]" --quiet
else
    info "Instalando latebra via PyPI..."
    pip install --upgrade pip --quiet
    pip install "latebra[all]>=${VERSION}" --quiet
fi

ok "latebra $VERSION instalado"

# ── Instalar navegadores (opcional) ──────────────
if command -v playwright >/dev/null 2>&1; then
    if [ "${LATEBRA_NO_BROWSER:-0}" = "0" ]; then
        info "Instalando navegadores Patchright..."
        playwright install chromium --quiet 2>/dev/null && ok "Chromium instalado" || warn "Chromium não instalado (opcional)"
    fi
fi

# ── Configurar MCP (Claude Desktop) ─────────────
MCP_CONFIG_FILE=""
if [ -f "$HOME/.config/Claude/claude_desktop_config.json" ]; then
    MCP_CONFIG_FILE="$HOME/.config/Claude/claude_desktop_config.json"
elif [ -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ]; then
    MCP_CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
fi

if [ -n "$MCP_CONFIG_FILE" ]; then
    if ! grep -q "latebra" "$MCP_CONFIG_FILE" 2>/dev/null; then
        info "Configurando MCP no Claude Desktop..."
        python3 -c "
import json, sys
try:
    with open('$MCP_CONFIG_FILE', 'r') as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}
config.setdefault('mcpServers', {})
config['mcpServers']['latebra'] = {
    'command': '$VENV_DIR/bin/latebra-mcp',
    'args': [],
    'env': {
        'LATEBRA_PROXIES': '${LATEBRA_PROXIES:-}',
        'LATEBRA_2CAPTCHA_KEY': '${LATEBRA_2CAPTCHA_KEY:-}',
    }
}
with open('$MCP_CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
" 2>/dev/null && ok "MCP configurado em: $MCP_CONFIG_FILE"
    else
        info "MCP já configurado em $MCP_CONFIG_FILE"
    fi
else
    warn "Claude Desktop não encontrado. Adicione manualmente ao seu cliente MCP:"
    echo "  Comando: $VENV_DIR/bin/latebra-mcp"
fi

# ── Wrap-up ──────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  🕶️  latebra instalado com sucesso!            ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Shell:${NC}    source $VENV_DIR/bin/activate"
echo -e "  ${BOLD}Testar:${NC}   latebra-mcp --version"
echo -e "  ${BOLD}Diretório:${NC} $INSTALL_DIR"
echo ""
echo -e "  ${YELLOW}Variáveis de ambiente opcionais:${NC}"
echo -e "  LATEBRA_PROXIES        — proxy1,proxy2,..."
echo -e "  LATEBRA_2CAPTCHA_KEY   — chave API 2Captcha"
echo -e "  LATEBRA_CAPSOLVER_KEY  — chave Capsolver"
echo ""
