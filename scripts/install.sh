#!/usr/bin/env bash
# Freeway — single installer that provisions BOTH runtimes locally:
#   - proxy/    (Python 3.14 via uv)      -> the data-plane endpoint (port 8082)
#   - frontend/ (Node via corepack pnpm)  -> dashboard + router daemon (port 19280)
#
# Local-only. Does not publish, push, or contact anything beyond fetching the
# dependencies each runtime needs to build/run on this machine.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_DIR="$ROOT/proxy"
FRONTEND_DIR="$ROOT/frontend"

log()  { printf '\033[1;36m[freeway]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[freeway] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---- proxy (Python / uv) --------------------------------------------------
command -v uv >/dev/null 2>&1 || fail "uv not found on PATH. Install: https://docs.astral.sh/uv/getting-started/installation/"
log "Provisioning proxy (uv sync) in $PROXY_DIR"
( cd "$PROXY_DIR" && uv sync )
log "Proxy ready. Run it with:"
log "    ( cd proxy && uv run uvicorn server:app --host 0.0.0.0 --port 8082 )"

# ---- frontend (Node / pnpm via corepack) ----------------------------------
command -v node >/dev/null 2>&1 || fail "node not found on PATH (Node >= 18 required)."
if ! command -v corepack >/dev/null 2>&1; then
  fail "corepack not found. It ships with Node >= 16.9; try 'npm i -g corepack'."
fi
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
log "Provisioning frontend (corepack pnpm install) in $FRONTEND_DIR"
( cd "$FRONTEND_DIR" && corepack pnpm install )
# Build web assets directly via vite (skips the ImageMagick favicon prestep).
log "Building frontend web dashboard (vite build)"
( cd "$FRONTEND_DIR" && corepack pnpm exec vite build )
log "Frontend ready. Run it with:"
log "    ( cd frontend && corepack pnpm start )"

log "Done. Both runtimes provisioned."
log "Or run the whole stack in Docker:  docker compose up --build"
