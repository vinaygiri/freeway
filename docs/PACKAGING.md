# Packaging & local deployment

Freeway is a two-process stack:

| Process | Dir | Port | Role |
|---|---|---|---|
| Proxy (FastAPI, Python/uv) | `proxy/` | 8082 | Data plane — the endpoint your tools point at (Claude Code / Codex / any OpenAI-compatible client). |
| Frontend (Node/pnpm) | `frontend/` | 19280 | Control plane — dashboard, model picker, router daemon. |

## Option A — single installer (native, both runtimes)

Provisions both runtimes on the host (uv for the proxy, corepack pnpm for the
frontend) and builds the web dashboard.

```bash
# macOS / Linux
./scripts/install.sh
```

```powershell
# Windows
.\scripts\install.ps1
```

Then run each process (the installer prints these):

```bash
( cd proxy && uv run uvicorn server:app --host 0.0.0.0 --port 8082 )
( cd frontend && corepack pnpm start )
```

Prereqs: `uv` on PATH, Node ≥ 18 with `corepack`.

## Option B — Docker (whole stack)

```bash
# 1. build the frontend web assets once (the frontend image copies web/dist):
( cd frontend && corepack pnpm install && corepack pnpm exec vite build )

# 2. optional: put provider keys in a local .env next to docker-compose.yml
#    (never commit it). See proxy/.env.example for the full key list.

# 3. bring the stack up
docker compose up --build
```

- Proxy → http://localhost:8082 (health: `GET /health`, admin UI: `/admin`, loopback-only)
- Frontend → http://localhost:19280

The proxy image (`proxy/Dockerfile`) is a two-stage uv build on
`python:3.14.0-slim` (patch pinned to `proxy/.python-version`), runs as a
non-root `freeway` user, and ships a `/health` HEALTHCHECK. It carries only the
default runtime dependencies — the optional `voice` / `voice_local` extras
(gRPC/torch) are **not** included.

## Not included (by design)

- **Opt-in telemetry** and **auto self-update** are intentionally omitted from
  this local build: they are outward/network features that can't be honestly
  verified in a local-only workflow. Wire them up in your own fork if you host
  Freeway as a service.
