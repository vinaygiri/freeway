<div align="center">

# 🚗💨 Freeway Proxy

### The data plane — a local gateway from your coding tool to 26 model providers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python 3.14](https://img.shields.io/badge/python-3.14-3776ab.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/packaging-uv-6340ac.svg?style=for-the-badge)](https://github.com/astral-sh/uv)
[![Tested with Pytest](https://img.shields.io/badge/testing-Pytest-00c0ff.svg?style=for-the-badge)](https://docs.pytest.org/)

**This is the Python/FastAPI proxy at the heart of Freeway.** For the full product overview, screenshots, and concepts, see the [top-level README](../README.md).

</div>

---

## What it is

Freeway Proxy is a **local, loopback-first gateway**. It accepts:

- **Claude Code's** Anthropic Messages traffic on `/v1/messages` (and `/v1/models`),
- **Codex's** OpenAI Responses traffic on `/v1/responses`,
- and generic **OpenAI Chat Completions** on `/v1/chat/completions`,

then routes each request to one of **26 providers** — preserving each client's wire protocol end to end. It adds the things free tiers need to actually be usable: quota-aware routing, automatic failover, adaptive request-fitting, health/circuit tracking, and a full control-center UI at `/admin`.

```
your tool ──Anthropic / OpenAI──▶  Freeway proxy (FastAPI)  ──▶  26 providers
(Claude Code / Codex / any            • protocol translation      (cloud free-tier
 OpenAI-compatible client)            • routing + failover          + local)
                                      • auto-fit + quota + circuit
                                      • /admin control center
```

---

## Quick start

**1. Install** (provisions uv, Python 3.14, Claude Code, Codex, and Freeway):

```powershell
# Windows
.\scripts\install.ps1
```
```bash
# macOS / Linux
./scripts/install.sh
```
> Open a **fresh terminal** afterward so the new `freeway` commands are on your PATH.

**2. Create config & start:**

```bash
freeway-init      # scaffolds ~/.freeway/.env
freeway           # starts the proxy + opens the admin UI (http://localhost:8082/admin)
```

**3. In the admin UI** (`/admin`): add a provider API key on **Providers**, pick a model on **Models** (click *Use*), then point your tool at Freeway:

```bash
freeway-claude    # Claude Code, routed through Freeway
freeway-codex     # Codex, routed through Freeway
```

Any other OpenAI-compatible tool can point its base URL at `http://localhost:8082/v1` and use the auth token from `~/.freeway/.env`.

### Run from source (development)

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

### Uninstall

Freeway installs locally (no remote installer), so it uninstalls locally too — the
scripts remove the `freeway-ai` uv tool and delete `~/.freeway/`:

```powershell
# Windows
.\scripts\uninstall.ps1
```
```bash
# macOS / Linux
./scripts/uninstall.sh
```
> Or by hand: `uv tool uninstall freeway-ai`, then remove the `~/.freeway/` directory.

---

## Providers (26)

**Cloud / free-tier (23):** NVIDIA NIM · OpenRouter · Gemini (Google AI Studio) · DeepSeek · Mistral · Mistral Codestral · OpenCode Zen · OpenCode Go · Wafer · Kimi · Cerebras · Groq · Fireworks · Cloudflare · Z.ai · SambaNova · Novita AI · OVHcloud AI Endpoints · Scaleway Generative APIs · Alibaba DashScope · GitHub Models · Ollama Cloud · Routeway

**Local (3):** llama.cpp · LM Studio · Ollama

A provider becomes available the moment you add a working key (or, for local ones, point Freeway at the endpoint) under **Providers** in the admin UI. Each provider is normalized to one of two transports (`openai_chat` or `anthropic_messages`) behind a shared protocol layer.

---

## Reliability — why "free" actually lasts

- **Auto-failover, including mid-request.** Requests are routed through a primary + fallback chain. If a provider is unavailable, rate-limited, or circuit-open, it's skipped up front; and if a provider *accepts* a request but then fails **before producing output** (rate-limit, overload, 5xx, bad model), Freeway re-routes to the next model and still completes — so a run never dies on one provider's hiccup.
- **Adaptive auto-fit (the 413/400 fix).** Over-budget requests are trimmed to the routed model's own context — largest non-essential tool schemas first, then the oldest whole turns — so a request can't be rejected for size. Only requests that would otherwise fail are touched.
- **Quota-aware routing + multi-key rotation.** Freeway tracks per-provider budgets and routes *away* from a provider before it rate-limits. Comma-separated keys (`PROVIDER_API_KEY=k1,k2,k3`) round-robin to multiply your per-minute budget.
- **Health probes + circuit breaker.** Background probes track real latency/availability; a failing provider's circuit opens so the next request routes around it.
- **Per-model verification.** One-click **⚡ Verify all** (or a model's **Test**) pings each model for real (✓ live + latency / ✗ down + reason) and saves the result.

---

## The Control Center (`/admin`)

A loopback-only UI served by `freeway` itself — every setting is editable and every feature observable, so you never hand-edit config files.

| Group | Pages |
|---|---|
| **Monitor** | Dashboard · Models · Activity · Limits · Health · Cache |
| **Configure** | Providers · Routing · Features · Privacy · Messaging |
| **Help** | User Guide (built-in manual) |

---

## Configuration

- Runtime config lives in **`~/.freeway/.env`** (scaffolded by `freeway-init`, edited via the admin UI).
- **`.env.example`** in this directory is the annotated reference of every setting (template only — not loaded at runtime).
- Logs: `~/.freeway/logs/`.

Key settings (all editable in the UI): `MODEL` (default routing target), `MODEL_FALLBACKS` (failover chain), `MODEL_DIRECTIVES` (`@`-alias table), `AUTO_FIT_MAX_TOKENS` (0 = auto), provider `*_API_KEY`s, and feature toggles.

---

## Development

Requires `uv` on PATH.

```bash
# Full local CI (repair mode: ruff format + ruff check --fix, then ty + pytest)
./scripts/ci.sh          # macOS / Linux
.\scripts\ci.ps1         # Windows

# Individual steps
uv run ruff format ; uv run ruff check --fix ; uv run ty check
uv run pytest -v --tb=short
uv run pytest tests/path/test_x.py::test_name   # single test
```

CI enforces five gates: banned-`# type: ignore` grep, ruff-format, ruff-check, ty, and pytest. See [`AGENTS.md`](AGENTS.md) (== `CLAUDE.md`) for the full engineering guide and [`ARCHITECTURE.md`](ARCHITECTURE.md) for the package map and request flow.

Live smoke tests (real providers) live under `smoke/` and are gated by `FCC_LIVE_SMOKE=1`; see [`smoke/README.md`](smoke/README.md).

---

## License & attribution

Licensed under the [MIT License](../LICENSE). Freeway is a derivative/combined work built on two MIT-licensed projects — **free-claude-code** (Ali Khokhar, [@Alishahryar1](https://github.com/Alishahryar1)) and **free-coding-models** (vava-nessa, [@vava-nessa](https://github.com/vava-nessa)). Their original notices are preserved in [`../LICENSES/`](../LICENSES) and summarized in [`../NOTICE`](../NOTICE). When redistributing, keep `LICENSE`, `NOTICE`, and `LICENSES/` intact.

This is an independent, community project — **not** affiliated with or endorsed by any AI model provider. You are responsible for complying with each provider's Terms of Service and for securing your own API keys.
