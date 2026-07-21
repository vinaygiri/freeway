<div align="center">

<img src="assets/banner.svg" alt="Freeway — run Claude Code & Codex on 26 free AI providers, with auto-failover and quota-aware routing" width="100%">

# 🚗💨 Freeway

### A free, smart route to many AI coding models.

**Freeway is a local gateway that lets [Claude Code](https://claude.com/claude-code), Codex, and any OpenAI‑compatible coding tool run on 26 model providers** (free‑tier cloud + local) — routing each request to the fastest healthy model that still has quota, automatically failing over, and trimming oversized requests so "free" actually lasts.

`brand: Freeway` · `command: freeway` · `package: freeway-ai` · MIT licensed

[![Python](https://img.shields.io/badge/python-3.14%2B-3776ab.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

<br>

<img src="docs/demo.gif" alt="Freeway control center — dashboard, model picker, routing, and live failover in the request inspector" width="820">

</div>

---

## Why Freeway?

Free AI model tiers are generous but fiddly: every provider speaks a slightly different API, each has its own per‑minute token limit, models go down, and coding tools like Claude Code send *huge* requests (every tool's schema, every turn) that blow past small free budgets with a **`413 request too large`**.

Freeway fixes all of that from **one local endpoint**:

- 🔌 **One endpoint, every tool** — accepts Claude Code's Anthropic protocol *and* Codex's / OpenAI's, and speaks to 26 providers behind the scenes.
- ⛽ **Make free last** — quota‑aware routing + multi‑key rotation stretch free tiers and route *away* from a provider before it rate‑limits.
- 🧠 **Smart routing** — health/latency/context‑aware model selection with automatic fallback chains and per‑message `@`‑directives.
- 🔬 **Know what's really live** — one‑click per‑model verification pings each model for real (✓ live + latency / ✗ down + reason) and saves the result, so "ready" isn't just a guess.
- 🩹 **Auto‑fit (the 413/400 fix)** — trims an over‑budget request (largest non‑essential tool schemas first, then the oldest conversation turns) so it can't be rejected. **Automatic by default** — sized to the model's own context, so it only touches requests that would otherwise fail. Core coding tools always kept.
- 🔒 **Trust & glass‑box** — data‑governance rules (never send code to training providers) + a full request inspector so you can *see* every routing decision.
- 🖥️ **Everything in a UI** — a local control center at `/admin` where every setting is editable and every feature is visible. No hand‑editing config files.

---

## Screenshots

**Dashboard** — is Freeway working, and what's it doing right now?

![Freeway Dashboard](docs/screenshots/dashboard.png)

**Models** — every model you can route to, ranked by quality (SWE‑bench) with live status & latency. Sort by Quality / Latency / Name, filter by Ready / All / ★ Favs, star favourites, and pick one (or add fallbacks) with a click. **⚡ Verify all** (or a model's **Test**) pings each model for real and marks it ✓ verified / ✗ down — saved until you re‑check.

![Freeway Models picker](docs/screenshots/models.png)

**Routing** — default model, fallback chain, `@`‑directive shortcuts, and auto‑fit, all explained inline.

![Freeway Routing](docs/screenshots/routing.png)

**Providers** — connect providers with a key; models appear on the Models page once a key works.

![Freeway Providers](docs/screenshots/providers.png)

**User Guide** — a built‑in manual covering setup, every page, and every concept.

![Freeway User Guide](docs/screenshots/guide.png)

---

## Quick start

**1. Install** — clone the repo and run the install script (provisions uv, Python, Claude Code, Codex, and Freeway):

```powershell
# Windows
git clone https://github.com/vinaygiri/freeway
cd freeway\proxy; .\scripts\install.ps1
```
```bash
# macOS / Linux
git clone https://github.com/vinaygiri/freeway
cd freeway/proxy && ./scripts/install.sh
```
> A one-line `uv tool install freeway-ai` (PyPI) is coming soon.
>
> Open a **fresh terminal** afterwards so the new `freeway` commands are on your PATH.

**2. Create config & start:**

```bash
freeway-init      # scaffolds ~/.freeway/.env
freeway           # starts the proxy + opens the admin UI (http://localhost:8082/admin)
```

**3. In the admin UI:** add a provider API key on **Providers**, pick a model on **Models** (click *Use*), then point your tool at Freeway:

```bash
freeway-claude    # Claude Code, routed through Freeway
freeway-codex     # Codex, routed through Freeway
```

That's it — you're coding on a free model. Auto‑fit keeps requests within the model's context automatically; for the smoothest experience use a **big‑context free provider** (Gemini, NVIDIA NIM) and add **multiple keys** per provider (`PROVIDER_API_KEY=k1,k2,k3`) to multiply your per‑minute budget.

---

## The Control Center (`/admin`)

Everything is configurable and observable from one loopback‑only UI served by `freeway` itself:

| Group | Page | What it does |
|---|---|---|
| **Monitor** | Dashboard | Live status: running?, active model, providers ready, cache hit‑rate. |
| | Models | The picker — all routable models with tier/SWE/latency, favourites, sort, filter, one‑click *Use* / *+Fallback*, and per‑model *Verify* (real ping). |
| | Activity | Every request (newest first): time, the **model that served it**, input tokens, primary‑vs‑fallback, and status — plus a "most recent" card showing what's running right now. |
| | Limits | Free‑tier token usage vs each provider's per‑minute budget. |
| | Health | Live provider stability + latency from background probes. |
| | Cache | Response‑cache hits/misses; clear button. |
| **Configure** | Providers | API keys, local endpoints, proxies. |
| | Routing | Default model, fallback chain, `@`‑directives, auto‑fit. |
| | Features | Toggle health probes, quota tracking, inspector, cache, web tools. |
| | Privacy | Hard data‑governance rules (no‑training / local‑only / region). |
| | Messaging | Optional Discord / Telegram + voice. |
| **Help** | User Guide | Built‑in manual: setup, pages, concepts, troubleshooting. |

---

## Key concepts

- **Favourites vs fallback.** ★ Favourite a model to shortlist it — a bookmark you can isolate with the **★ Favs** filter; it does *not* change routing. **Fallback** is real routing: **+ Fallback** adds a model to the failover chain that's tried, in order, when your primary is unavailable (toggle it off with **✓ Fallback**).
- **Auto‑failover (never stops).** If your model's provider is down or rate‑limited, Freeway automatically tries the next model in your chain — *including mid‑request*: when a provider accepts a request but then fails before producing output (rate‑limit, overload, 5xx, bad model), Freeway re‑routes to the next model and still completes, so a run never dies on one provider's hiccup. With a handful of keys across providers, it just keeps going.
- **`@`‑Directives.** Define aliases like `fast=groq/llama-3.3-70b-versatile, big=cerebras/gpt-oss-120b`, then type `@big refactor this` to route that one message to Cerebras.
- **Auto‑fit.** Automatic by default (budget = 90% of the routed model's context): trims the largest non‑essential tools, then the oldest whole turns, so a request can't 413/400 — only touching requests that would exceed the model's window. Set **Routing → Auto‑fit Budget** explicitly only for tiers that cap *below* their advertised context.
- **Bounded long sessions.** The whole conversation is resent each turn, so it grows. `freeway-claude` sizes Claude Code's compaction window to your budget/model so long sessions compact instead of overflowing. For durable free‑tier use: a **big‑context provider** (Gemini 1M, NVIDIA NIM 128k) + **multiple keys** (`PROVIDER_API_KEY=k1,k2,k3` → round‑robin, N× the per‑minute budget). **Codex** also sends ~10× smaller requests than Claude Code.
- **Model selection.** *Use* on the Models page sets what everything routes to — you don't pick in the CLI. Freeway maps each request to the *current* default, so a change applies to the **next request automatically** (no restart). Only exception: a model you pinned via Claude Code's own `/model` overrides the default for that session.
- **"Ready" vs "Verified".** *Ready* is provider‑level and optimistic (a healthy provider marks all its models ready). *Verified* is a real per‑model ping via **⚡ Verify all** / **Test** — ✓ live + latency or ✗ down + reason, saved until you re‑check. Actual availability is otherwise proven at request time by failover.

---

## Deployment

**Native (both runtimes):** `scripts/install.ps1` / `install.sh` provision uv + Node and install Freeway.

**Docker (whole stack):**
```bash
( cd frontend && corepack pnpm install && corepack pnpm exec vite build )   # build web assets once
docker compose up --build
```
Proxy → `http://localhost:8082` · Frontend dashboard → `http://localhost:19280`. See [`docs/PACKAGING.md`](docs/PACKAGING.md).

---

## Architecture

```
your tool ──Anthropic / OpenAI──▶  Freeway proxy (FastAPI)  ──▶  26 providers
(Claude Code / Codex)               • protocol translation        (Groq, Cerebras,
                                     • health / quota / circuit      SambaNova, Gemini,
                                     • fallback + auto-fit            OpenRouter, local…)
                                     • /admin control center
```

- `proxy/` — the data plane (Python / uv / FastAPI). Protocol translation, routing, and the admin UI. Run `uv run pytest` to test.
- `frontend/` — the optional rich dashboard / model catalog (Node / pnpm).
- `docs/` — `ROADMAP.md`, `FEATURE_MERGE_PLAN.md`, `PRODUCT_DIFFERENTIATION.md`, `PACKAGING.md`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `413` / `400 context_length_exceeded` | Auto‑fit handles it by default. If a tier caps below its advertised context, set **Routing → Auto‑fit Budget** explicitly (e.g. 7000), use a **big‑context provider** (Gemini/NIM), add **multiple keys** (`PROVIDER_API_KEY=k1,k2,k3`), or switch to **Codex** (~10× smaller requests). Note: 8k‑limit tiers (Groq/Cerebras free) can't fit Claude Code's ~42k baseline at all. |
| Port already in use | Change **Providers → Runtime → PORT** (default 8082) and Apply. |
| "no key" on a provider | Add its API key under **Providers**, Apply, then *Refresh models*. |
| `command not found` after install | Open a fresh terminal (PATH updates apply to new shells only). |
| Config / logs | `~/.freeway/.env` (from `freeway-init`); logs in `~/.freeway/logs/`. |

---

## Contributing & Community

Contributions are welcome! Please read:

- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — dev setup, the CI gates, and the PR process
- [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) — how we work together
- [`SECURITY.md`](./SECURITY.md) — how to report a vulnerability privately (please don't open a public issue for security problems)

## Changelog

Release history and notable changes are in [`CHANGELOG.md`](./CHANGELOG.md). The current version is in `proxy/pyproject.toml`.

## Credits & Attribution

Freeway is a derivative/combined work built on two MIT‑licensed projects — huge thanks to their authors:

| Upstream | Author | Source |
|---|---|---|
| **free-claude-code** | Ali Khokhar ([@Alishahryar1](https://github.com/Alishahryar1)) | https://github.com/Alishahryar1/free-claude-code |
| **free-coding-models** | vava-nessa ([@vava-nessa](https://github.com/vava-nessa)) | https://github.com/vava-nessa/free-coding-models |

## License

Licensed under the [MIT License](./LICENSE). This project incorporates code from the upstream projects above; their original MIT notices are preserved in [`LICENSES/`](./LICENSES) and continue to apply to their portions. See [`NOTICE`](./NOTICE) for the attribution summary. When redistributing, keep `LICENSE`, `NOTICE`, and `LICENSES/` intact.

## Disclaimer

This is an independent, community‑developed project. It is **not** affiliated with, endorsed by, or sponsored by the upstream authors or by any AI model provider (NVIDIA, Groq, Google, Mistral, Anthropic, OpenAI, etc.). Provider and product names are used only to describe technical compatibility. You are responsible for complying with each provider's Terms of Service and for securing your own API keys.
