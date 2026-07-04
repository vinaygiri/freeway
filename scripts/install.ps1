# Freeway - single installer that provisions BOTH runtimes locally (Windows/PowerShell).
#   - proxy\    (Python 3.14 via uv)      -> data-plane endpoint (port 8082)
#   - frontend\ (Node via corepack pnpm)  -> dashboard + router daemon (port 19280)
#
# Local-only. Does not publish, push, or contact anything beyond fetching the
# dependencies each runtime needs to build/run on this machine.
$ErrorActionPreference = 'Stop'

$Root       = Split-Path -Parent $PSScriptRoot
$ProxyDir   = Join-Path $Root 'proxy'
$FrontendDir = Join-Path $Root 'frontend'

function Log  { param($m) Write-Host "[freeway] $m" -ForegroundColor Cyan }
function Fail { param($m) Write-Host "[freeway] ERROR: $m" -ForegroundColor Red; exit 1 }

# ---- proxy (Python / uv) --------------------------------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Fail "uv not found on PATH. Install: https://docs.astral.sh/uv/getting-started/installation/"
}
Log "Provisioning proxy (uv sync) in $ProxyDir"
Push-Location $ProxyDir
try { uv sync } finally { Pop-Location }
Log "Proxy ready. Run it with:"
Log "    cd proxy; uv run uvicorn server:app --host 0.0.0.0 --port 8082"

# ---- frontend (Node / pnpm via corepack) ----------------------------------
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Fail "node not found on PATH (Node >= 18 required)."
}
if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    Fail "corepack not found. It ships with Node >= 16.9; try 'npm i -g corepack'."
}
$env:COREPACK_ENABLE_DOWNLOAD_PROMPT = '0'
Log "Provisioning frontend (corepack pnpm install) in $FrontendDir"
Push-Location $FrontendDir
try {
    corepack pnpm install
    Log "Building frontend web dashboard (vite build)"
    corepack pnpm exec vite build
} finally { Pop-Location }
Log "Frontend ready. Run it with:"
Log "    cd frontend; corepack pnpm start"

Log "Done. Both runtimes provisioned."
Log "Or run the whole stack in Docker:  docker compose up --build"
