# ┌─────────────────────────────────────────────────────┐
# │  latebra v0.2.0 — Single-Command Windows Installer  │
# │  irm https://latebra.evandro.app/install.ps1 | iex   │
# │  Autor: Evandro Fonseca Junior                      │
# │  Licença: MIT                                       │
# └─────────────────────────────────────────────────────┘
#Requires -Version 7.0

param(
    [string]$InstallDir = "$env:USERPROFILE\.latebra",
    [string]$Version = "0.2.0",
    [switch]$NoBrowser = $false,
    [string]$RepoUrl = "https://github.com/evandrofjs/latebra.git"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ── Banner ───────────────────────────────────────
Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    🕶️  latebra anti-bot MCP installer     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Helpers ──────────────────────────────────────
function Write-Info  { Write-Host "→ $args" -ForegroundColor Cyan }
function Write-OK    { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "✗ $args" -ForegroundColor Red; exit 1 }

# ── Pre-flight checks ────────────────────────────
Write-Info "Verificando requisitos..."

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Err "Python não encontrado. Instale: winget install Python.Python.3.12"
}

$pyVersion = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyMajor = [int]($pyVersion -split '\.')[0]
$pyMinor = [int]($pyVersion -split '\.')[1]

if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 12)) {
    Write-Err "Python 3.12+ é necessário (atual: $pyVersion). Instale via winget: winget install Python.Python.3.12"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Err "Git não encontrado. Instale: winget install Git.Git"
}

Write-OK "Python $pyVersion encontrado"

# ── Criar diretório ──────────────────────────────
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# ── Virtual environment ──────────────────────────
$VenvDir = Join-Path $InstallDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Info "Criando ambiente virtual em $VenvDir..."
    & $python.Source -m venv $VenvDir
    Write-OK "Ambiente virtual criado"
} else {
    Write-Info "Ambiente virtual existente em $VenvDir"
}

# ── Activar venv ─────────────────────────────────
$VenvPython = Join-Path $VenvDir "Scripts" "python.exe"
$VenvPip = Join-Path $VenvDir "Scripts" "pip.exe"

# ── Instalar latebra ─────────────────────────────
$RepoDir = Join-Path $InstallDir "repo"
if (Test-Path (Join-Path $RepoDir "pyproject.toml")) {
    Write-Info "Repositório existente, atualizando via git pull..."
    Push-Location $RepoDir
    git pull --ff-only origin main 2>$null
    Pop-Location
} else {
    Write-Info "Clonando latebra v$Version..."
    git clone --branch main $RepoUrl $RepoDir 2>$null
    if (-not (Test-Path (Join-Path $RepoDir "pyproject.toml"))) {
        Write-Info "Repo não disponível, instalando via pip..."
        $RepoDir = $null
    }
}

Push-Location (if ($RepoDir) { $RepoDir } else { $InstallDir })

Write-Info "Instalando latebra..."
& $VenvPip install --upgrade pip --quiet 2>$null

if ($RepoDir) {
    & $VenvPip install -e ".[all]" --quiet 2>$null
} else {
    & $VenvPip install "latebra[all]>=${Version}" --quiet 2>$null
}

Write-OK "latebra $Version instalado"
Pop-Location

# ── Instalar navegadores (opcional) ──────────────
$Playwright = Join-Path $VenvDir "Scripts" "playwright.exe"
if ((Test-Path $Playwright) -and (-not $NoBrowser)) {
    Write-Info "Instalando navegadores Patchright..."
    & $Playwright install chromium 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Chromium instalado"
    } else {
        Write-Warn "Chromium não instalado (opcional)"
    }
}

# ── Configurar MCP (Claude Desktop) ──────────────
$ClaudeConfigPath = Join-Path $env:APPDATA "Claude" "claude_desktop_config.json"
if (Test-Path $ClaudeConfigPath) {
    $config = Get-Content $ClaudeConfigPath -Raw | ConvertFrom-Json -AsHashtable
    if (-not $config.mcpServers) { $config.mcpServers = @{} }
    if (-not $config.mcpServers.latebra) {
        Write-Info "Configurando MCP no Claude Desktop..."
        $latebraExe = Join-Path $VenvDir "Scripts" "latebra-mcp.exe"
        $config.mcpServers.latebra = @{
            command = $latebraExe
            args = @()
            env = @{
                LATEBRA_PROXIES = $env:LATEBRA_PROXIES ?? ""
                LATEBRA_2CAPTCHA_KEY = $env:LATEBRA_2CAPTCHA_KEY ?? ""
            }
        }
        $config | ConvertTo-Json -Depth 10 | Set-Content $ClaudeConfigPath
        Write-OK "MCP configurado em: $ClaudeConfigPath"
    } else {
        Write-Info "MCP já configurado"
    }
} else {
    Write-Warn "Claude Desktop não encontrado. Adicione manualmente ao seu cliente MCP:"
    Write-Host "  Comando: $VenvDir\Scripts\latebra-mcp.exe"
}

# ── Wrap-up ──────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  🕶️  latebra instalado com sucesso!            ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Shell:     $VenvDir\Scripts\Activate.ps1"
Write-Host "  Testar:    latebra-mcp --version"
Write-Host "  Diretório: $InstallDir"
Write-Host ""
Write-Host "  Variáveis de ambiente opcionais:" -ForegroundColor Yellow
Write-Host "  `$env:LATEBRA_PROXIES        — proxy1,proxy2,..."
Write-Host "  `$env:LATEBRA_2CAPTCHA_KEY   — chave API 2Captcha"
Write-Host ""
