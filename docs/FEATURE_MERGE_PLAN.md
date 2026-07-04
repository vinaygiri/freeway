# Feature-Merge Plan

Combining **free-claude-code (FCC)** and **free-coding-models (FCM)** into one tool.

## 1. Guiding decision

The two projects are mirror images:

- **FCC (Python/FastAPI)** owns the *protocol layer* — Anthropic Messages, OpenAI
  Responses, thinking/tool/SSE translation. This is hard, subtle, and backed by
  ~1691 tests. **Reimplementing it in Node would be high-risk and low-value.**
- **FCM (Node)** owns *model intelligence + UX* — live benchmarking, a
  stability score, a failover/circuit-breaker router, and a mature TUI + web +
  desktop UI plus config-writers for ~19 tools. This logic is valuable but
  **reimplementable**, and the UI is reusable as-is.

**Therefore:** FCC stays the runtime **data plane**. FCM's routing/benchmark
intelligence is ported *into* FCC (Python), and FCM's UI is repurposed as the
**control plane** that drives FCC over its API. Nothing that is hard to port
gets ported.

## 2. Target architecture

```
                 ┌─────────────────────────── Control plane (Node, from FCM) ───────────────────────────┐
                 │  TUI  ·  Web dashboard  ·  Tauri desktop  ·  tool config-writers (OpenCode/Goose/…)   │
                 └───────────────▲───────────────────────────────────────────────▲─────────────────────┘
                                 │ admin/stats/health API (HTTP)                  │ writes tool configs → point at proxy
                 ┌───────────────┴───────────────────────────────────────────────┴─────────────────────┐
                 │                         Data plane (Python/FastAPI, from FCC)                          │
   Claude Code → │  /v1/messages    ┐                                                                     │
        Codex  → │  /v1/responses   ├─► protocol translation ─► INTELLIGENT ROUTER ─► provider transports │→ providers
   any OA tool → │  /v1/chat/…(new) ┘                              ▲                                       │
                 │                            benchmark + health store (ported from FCM)                  │
                 └────────────────────────────────────────────────────────────────────────────────────── ┘
```

Two processes (Python proxy + Node UI), one product. The UI never proxies model
traffic; it only reads stats and writes config. All model traffic flows through
the Python proxy, so Claude Code, Codex, and generic OpenAI tools are all served
by one endpoint backed by health-aware routing.

## 3. Direction of each feature port

| Feature | From → To | Effort | Notes |
|---|---|---|---|
| Anthropic Messages / Responses / protocol translation | keep in FCC | — | Do **not** touch; it's the core asset |
| `/v1/chat/completions` client endpoint | add to FCC | S | FCC already has OpenAI-chat transport internally; expose it inbound |
| Live benchmarking + stability score (p95/jitter/spike/uptime) | FCM → FCC (port) | M | Port the scoring math + probe loop to Python; reuse FCM's test vectors |
| Failover / circuit breaker / health-probe routing | FCM → FCC (port) | L | Replace FCC's static tier routing with health-aware selection |
| Model "sets" + auto-heal | FCM → FCC (port) | M | Depends on health store |
| TUI / web dashboard / desktop | reuse FCM UI | M | Re-point at FCC's API instead of FCM's daemon |
| Config-writers for ~19 tools | reuse FCM | S | Point tools at the unified proxy URL |
| Per-tier routing (Opus/Sonnet/Haiku) | keep in FCC | — | Compose with new router |
| Discord/Telegram remote sessions, voice | keep in FCC | — | Surface toggles in unified UI |
| Local server tools (web_search/web_fetch), request optimizations | keep in FCC | — | — |
| Provider catalog | merge both | M | Union of provider sets into one catalog |
| Docker image | FCM → combined | S | Containerize the two-process stack |
| Telemetry (opt-in), auto self-update | FCM → combined | S | Wire to the packaged product |

S ≈ ≤1 wk · M ≈ 1–2 wk · L ≈ 2–4 wk (rough, single dev).

## 4. Phased roadmap

Each phase ends in a **locally buildable + testable** state (no git/remote per
repo rulebook): Node = `corepack pnpm test`, Python = `uv run pytest`.

### Phase 0 — Monorepo scaffold (baseline)
- Layout: `freeway/{proxy (FCC), frontend (FCM), docs, LICENSES}`.
- Bring both codebases in unchanged; confirm both still build/test locally.
- **DoD:** `uv run pytest` green in `proxy/`, `corepack pnpm test` green in `frontend/` (minus known Windows-only test skips), license/attribution in place.

### Phase 1 — Unify the endpoint surface
- Add inbound `POST /v1/chat/completions` to FCC, reusing its existing
  OpenAI-chat transport and model router.
- **Win:** one proxy now serves Claude Code (`/v1/messages`), Codex
  (`/v1/responses`), *and* every generic OpenAI-compatible tool.
- **DoD:** new route has contract tests; a chat completion streams through a real provider (local smoke).

### Phase 2 — Benchmark / health data plane
- Port FCM's ping loop + stability score (p95 30% · jitter 30% · spike 20% ·
  uptime 20%) into a Python background service maintaining a per-model health
  store. Expose read-only `/admin/health` + `/stats`.
- **DoD:** unit tests on the scoring math (reuse FCM vectors); a probe cycle populates the store; endpoints return live data.

### Phase 3 — Intelligent router (the core win)
- Replace FCC's static per-tier resolution with a **health-aware router**:
  best healthy model per tier/set, failover on 429/5xx/timeout, circuit
  breaker, auth-error isolation (skip a provider's remaining models on 401/403),
  retry-before-first-byte for streams. Introduce the "set" concept.
- **DoD:** contract tests simulate provider failures → deterministic failover; circuit-breaker state transitions covered; per-tier overrides still honored.

### Phase 4 — Frontend as control plane
- Re-point FCM's TUI + web + desktop at FCC's admin/stats/health APIs: live
  benchmark table, validate/apply config, model/set picker, Smart Recommend,
  Playground (against `/v1/chat/completions`), command palette.
- Keep FCM's tool config-writers; have them target the unified proxy URL.
- **DoD:** web build passes; TUI smoke (spawn + capture); selecting a model in the UI updates FCC config and takes effect on the next request.

### Phase 5 — Absorb remaining differentiators
- Merge provider catalogs (union). Surface FCC's Discord/Telegram + voice as
  toggles in the unified UI. Add a Docker image for the two-process stack.
  Opt-in telemetry + auto-update wired to the packaged product.
- **DoD:** union catalog validated; Docker image runs both processes; toggles work end-to-end.

### Phase 6 — Consolidation & polish
- One provider-metadata source of truth (dedupe FCC catalog vs FCM `sources.js`).
- Unified token/usage analytics. Single installer that provisions both runtimes
  (uv + Node). Docs pass.
- **DoD:** no duplicated provider definitions; one-command local bring-up; docs match behavior.

## 5. Key risks & open decisions

1. **Benchmark engine language (load-bearing).** Recommended: reimplement in
   Python (single data plane, no IPC). Faster interim alternative: keep FCM's
   Node engine as a **sidecar** that writes a health JSON the Python router
   reads — lower upfront cost, but two runtimes in the data path and a sync
   seam. Pick before Phase 2.
2. **Two-runtime footprint.** Product now needs both Python (uv) and Node. The
   Phase 6 installer must make this painless; Docker (Phase 5) hides it for
   server use.
3. **Config source of truth.** FCC's managed `~/.fcc` config vs FCM's
   `~/.free-coding-models.json`. Unify on FCC's managed config early (Phase 4)
   so the UI has one place to write.
4. **Provider-catalog drift.** Two catalogs will diverge until Phase 6; treat
   FCC's as authoritative for routing and map FCM entries into it.
5. **Cross-surface parity (FCM mandate).** Any UI feature must work on TUI +
   web + desktop — carry this rule into the merged frontend.

## 6. Suggested order of value

`Phase 1 (unify endpoints)` → `Phase 3 (failover router)` deliver most of the
user-visible win (one resilient endpoint for all tools). `Phase 2` is the
prerequisite for 3. `Phase 4` makes it pleasant. `5–6` are breadth/polish.
