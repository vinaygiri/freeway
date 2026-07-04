# Roadmap — Combined Project

Tracked build checklist. Detail lives in [`FEATURE_MERGE_PLAN.md`](./FEATURE_MERGE_PLAN.md)
and [`PRODUCT_DIFFERENTIATION.md`](./PRODUCT_DIFFERENTIATION.md).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done.
Each milestone ends **locally buildable + testable** (Python `uv run pytest`,
Node `corepack pnpm test`) — no git/remote needed.

---

## Milestone 0 — Scaffold  *(foundation)* ✅
- [x] License + attribution setup (`LICENSE`, `NOTICE`, `LICENSES/`)
- [x] Design docs (merge plan, differentiation, roadmap)
- [x] Name locked: **Freeway** (brand) · `freeway` (CLI) · `freeway-ai` (npm/repo)
- [x] Monorepo layout: `proxy/` (FCC), `frontend/` (FCM), `docs/`, `LICENSES/`
- [x] Import both codebases; both build green locally
  - proxy: `uv sync` OK · pytest **1690 passed, 8 skipped, 1 failed** — the 1 fail
    is `test_ci_sh_is_tracked_executable` (runs `git ls-files`; expected fail with
    no git repo per rulebook, not a code issue)
  - frontend: `pnpm install` OK · **536/542 pass**; the 6 fails are the known
    Windows-only assertions (`/` path separators, `zsh/bash/fish` shell) — identical
    to the standalone run, nothing new from the merge

## Milestone 1 — Unify endpoints  *(Merge P1 — biggest early win)* ✅
- [x] Add inbound `POST /v1/chat/completions` to the proxy (streaming + non-streaming)
  - New `core/openai_chat_completions/` adapter (request converter, stream assembler,
    SSE + aggregation), `api/models/openai_chat_completions.py`,
    `api/handlers/chat_completions.py`, route + probe in `api/routes.py`
  - Reuses the existing provider-execution pipeline + model router unchanged
- [x] Tests: 20 new (12 API integration + 8 converter unit) — all green
- [x] Gates: ruff format/check, ty, ban-type-ignore all clean; full suite
  **1710 passed / 8 skipped** (only the no-git `test_ci_sh_is_tracked_executable` fails)
- [ ] Real-provider local smoke — deferred (needs configured API keys; TestClient
  integration covers route→handler→convert→pipeline→assembler end-to-end)
- [x] Result: one proxy now serves Claude Code (`/v1/messages`) + Codex
  (`/v1/responses`) + any OpenAI tool (`/v1/chat/completions`)

## Milestone 2 — Benchmark / health plane  *(Merge P2)* ✅
- [x] Port FCM stability score (p95/jitter/spike/uptime, weights 0.3/0.3/0.2/0.2)
  to Python — `core/health/score.py` (pure, measurable=200/401, verdict logic)
- [x] `HealthStore` (`core/health/store.py`) — bounded ring buffer per target
  (improves on FCM's unbounded history)
- [x] Background probe loop — `api/health_probe.py` `HealthProbeService`, mirrors
  `ProviderModelDiscovery`; probes each provider via cheap `list_model_ids()`
  (**zero completion-quota cost**), owned by `AppRuntime`, gated by settings
- [x] Read endpoints: public `GET /v1/health/stats` + admin `GET /admin/api/health`
- [x] Settings: `ENABLE_HEALTH_PROBES`, `HEALTH_PROBE_INTERVAL_SECONDS`,
  `HEALTH_PROBE_SAMPLE_WINDOW`
- [x] Tests: 28 new (score parity w/ FCM cases + store + endpoints + probe);
  full suite **1738 passed / 8 skipped** (only no-git fail); ruff+ty+ban clean
- [x] Benchmark-engine language decision: **resolved in favor of Python reimpl**
  (single data plane, no sidecar) — the deferred fork is now closed
- ~~Node sidecar option~~ — dropped
- **Note:** active probing measures *provider-level* latency. Richer *per-model*
  latency will come **passively from real request traffic** in M4 (router),
  where it's consumed — zero added quota cost (a proxy advantage over FCM)

## Milestone 3 — Quota Governor  *(D1 — flagship)* ✅
- [x] Provider limits catalog — `config/provider_quota.py` (`ProviderQuotaLimit` +
  `PROVIDER_QUOTA_LIMITS`: nvidia_nim/groq/cerebras/open_router/codestral/cloudflare;
  ported from FCM, keyed to proxy provider ids)
- [x] Live consumption tracking — `core/quota.py` `QuotaTracker` (pure, injectable
  clock, rolling 60s/24h windows), recorded at the `provider_execution.stream()`
  choke point (**no stream-wrapping** — low risk); threaded via optional
  `quota_tracker=None` through 3 handlers + route factories
- [x] Governor — `api/quota_governor.py` `QuotaGovernor`: utilization,
  ok/warning/exhausted status, **`avoid` flag at ≥95%** (the proactive
  route-away signal the M4 router will consume), `seconds_to_exhaustion`
- [x] Endpoints: public `GET /v1/quota/stats` (fuel gauge) + admin `GET /admin/api/quota`
- [x] Setting `ENABLE_QUOTA_TRACKING`; tracker+governor owned by `AppRuntime`
- [x] Tests: 18 new (catalog + tracker windows + governor verdicts + endpoints +
  integration proving a real request records consumption); full suite
  **1756 passed / 8 skipped** (only no-git fail); ruff+ty+ban clean
- **Deferred to M4:** output-token capture (needs SSE wrapping) and actual
  route-away wiring (needs the multi-candidate router). Tracker already accepts a
  token arg so token accounting extends without rework.

## Milestone 4 — Intelligent router  *(Merge P3 + D2 + D3)* — sliced

**Key finding:** the transports swallow mid-stream failures into (often
success-shaped) SSE, so cross-provider failover can't be a naive outer wrapper.
"Route away before the 429" is achieved at *selection* time (skip avoid/open
candidates) — safe; mid-stream failover needs transport surgery (M4b).

### M4a — Failover + circuit breaker + health/quota-aware selection ✅
- [x] Fallback chain config: `MODEL_FALLBACKS` (comma-sep provider/model refs) +
  `ModelRouter.resolve_fallback_candidates()`
- [x] Circuit breaker — `core/circuit.py` (ported FCM state machine: 3-fail
  threshold, 30s→300s exponential backoff, CLOSED/OPEN/HALF_OPEN, injectable clock)
- [x] `api/router_policy.py` `RoutingPolicy` — dedupe + usable-first ordering,
  consuming **all three planes**: skip circuit-open, quota-`avoid`, health-`Not Active`
- [x] Pre-flight/resolution failover in `ProviderExecutionService.stream_with_failover()`
  (auth poison-skips provider; HTTPException+ProviderError handled; raises on exhaust);
  transparent to handlers (drop-in for `stream()`)
- [x] Circuit breaker owned by `AppRuntime`; admin `GET /admin/api/router` (fallbacks + circuit snapshot)
- [x] 19 new tests; full suite **1775 passed / 8 skipped** (only no-git fail); ruff+ty+ban clean

### M4b — Mid-stream cross-provider failover *(risky; deferred)*
- [ ] Thread a failure signal out of `RecoveryController` at the uncommitted-holdback seam

### M4c — Multi-key pooling / rotation *(net-new; not in FCM daemon)* ✅
- [x] Comma-separated keys per provider (existing key env var) → `ProviderConfig.api_keys`
- [x] `providers/key_pool.py` `KeyPool` — round-robin, dedupe, injectable
- [x] Native transports: `_api_key` is a pool-backed property (rotates per request;
  **zero per-provider changes**). OpenAI-chat: **one client per key** (no shared-client
  race), selected per request. Ollama placeholder key preserved via pool.
- [x] Rotation multiplies free-tier headroom (~1/N traffic per key)
- [~] **429 parking/revival deferred** — needs key-identity threading through the
  error path; rotation shipped, parking is a clean follow-up
- [x] 11 new tests; regressions caught+fixed (openai-chat cleanup, Ollama default)

### M4d — Capability + context-window routing ✅
- [x] `ProviderModelInfo.context_window` (+ captured from OpenRouter `context_length`);
  cache/runtime `cached_model_info` accessor
- [x] `RoutingPolicy` context-window guard: **deprioritize** (never drop) candidates
  whose known window < request tokens; unknown windows treated as usable
- [x] `stream_with_failover` computes request tokens; policy injected with model lookup
- [x] 9 new tests. **Caveat:** only OpenRouter exposes context size today, so the
  guard is a no-op elsewhere until more per-model metadata is added (vision/tools deferred)

### M4b — Mid-stream cross-provider failover *(DEFERRED — high risk)*
Investigated; a provably-safe seam exists but shipping is HIGH-risk with broad
blast radius. Deferred by decision. **Captured design for a future attempt:**
- **Safe seam:** the `not committed` path only. Recovery holds back all output
  for 0.75s / 64KB (`core/anthropic/streaming/recovery.py`, `RecoveryHoldbackBuffer`);
  **no bytes (not even `message_start`) reach the client before commit** — locked
  by `test_precommit_openai_holdback_retries_without_leaking_partial`. The
  `EARLY_RETRY` branch is entered only when `not committed`, so failing over there
  cannot double-emit / corrupt.
- **Work required:** (1) new `CrossProviderFailover` exception raised **only** on
  the uncommitted path in both `providers/transports/{openai_chat,anthropic_messages}/stream.py`
  (instead of same-provider `continue` / error-SSE-emit); (2) new `RecoveryController`
  action/policy to signal hand-off; (3) convert `ProviderExecutionService.stream_with_failover`
  into a **stream-driving async generator** that holds back until commit, then yields
  — re-driving the next candidate on the failover signal (breaks M4a's sync-return
  test contract).
- **Catastrophic failure mode to guard:** never trigger failover when `committed is True`
  (a fast provider that commits then fails would make provider B emit a 2nd
  `message_start` → unrecoverable stream corruption). Every trigger MUST hard-gate
  on `recovery.committed is False`.
- **Why deferrable:** M4a already fails over on pre-flight failures (auth/down/
  bad-config/circuit-open/quota-avoid) + same-provider early-retry handles transient
  blips; M4b only adds the narrow after-connect-before-first-byte window.

## Milestone 5 — Inline model directives  *(D3.5 — quick win)* ✅
- [x] `@`-mention parser — `api/directives.py`: standalone tokens in the latest user
  turn, **code-fence-safe**, resolves `@provider/model` directly or via alias table
- [x] Alias table from `MODEL_DIRECTIVES` (`key=provider/model, …`) + `@provider/model` inline
- [x] Conflict rule: first distinct target wins, rest reported as `ignored`; repeats aren't conflicts
- [x] Directive token stripped from the prompt before forwarding (unresolved `@x` left intact)
- [x] Integrated in `ModelRouter.resolve_messages_request` — covers Claude Code + Codex + OpenAI-chat at once
- [x] 12 tests; full suite **1802 passed / 8 skipped** (only no-git fail); ruff+ty+ban clean
- **Deferred to M6 (frontend):** the graphical config UI (TUI/web/desktop alias-table editor,
  live model picker, lint, per-repo scope, JSON import/export)
- **Deferred:** semantic auto-classes (`@best`/`@fast` as *ranked* selections) + sticky
  session pins (`@groq!`) — need ranking / session state

## Milestone 6 — Control plane / frontend  *(Merge P4 + D4)* — sliced

### M6a — Request Inspector data plane (proxy) ✅
- [x] `core/recent_requests.py` `RecentRequestStore` (count-bounded ring buffer;
  metadata only — no prompt content)
- [x] Recorded synchronously in `stream_with_failover` via `RoutingPolicy.record_request`
  (no new handler params — hung on the already-injected policy); off the streaming path
- [x] `RoutingPolicy.classify()` surfaces the skip/demote reason (circuit/quota/health/context)
  → captured as each request's `downgrade_reason` + `was_fallback`
- [x] Owned by `AppRuntime` (`enable_request_inspector`, `request_inspector_window`);
  admin `GET /admin/api/requests`
- [x] 16 tests; full suite **1811 passed / 8 skipped** (only no-git fail); ruff+ty+ban clean
- **Deferred:** true mid-stream terminal outcome (needs streaming-path wrapping)

### M6b — Frontend integration (Node) — tool re-point + web Inspector ✅ *(chosen slice)*
- [x] **Tool re-point:** shared `getProxyBaseUrl()` in `endpoint-installer.js` (override via
  `FREEWAY_PROXY_URL`, else local FCM port); the `fcm_router` tool base-URL now routes through
  it, so coding tools can be pointed at Freeway's proxy. Default behavior preserved. 3 tests.
- [x] **Web Request Inspector:** `web/server.js` `/api/proxy/requests` pass-through →
  proxy's loopback `/admin/api/requests`; `useRequestInspector` hook; `RequestInspectorView.jsx`
  (recent routing decisions table); wired into `App.jsx` + Header nav.
- [x] Verified: `node --check` server.js OK, `vite build` compiles clean, frontend suite
  **539/545** (6 unchanged Windows-only fails; **0 new**).
- ⚠️ **Visual/runtime UI not exercised here** (would need the web dev server + browser / tmux) —
  compilation + test-suite verified only.
- **Deferred (per decision):** TUI inspector overlay, cross-surface alias-table editor,
  Tauri desktop shell (unbuilt), and full 3-backend ownership reconciliation.

### M6b (full cross-surface) — remaining / deferred
Investigation findings: the frontend is **large** and has **two Node backends already**
(`web/server.js:3333` + `router-daemon.js:19280`, both serving `/api`), a request log
already exists in the daemon, **desktop (Tauri) is unbuilt greenfield**, and the TUI is
~5000 LOC of hand-rolled ANSI. Introducing the FastAPI proxy as a third backend needs an
**architecture decision** (which backend owns health/quota/router/inspector). Recommended
first slice: **web-dashboard-only Request Inspector** reading the proxy via a `web/server.js`
pass-through (clone `RouterView.jsx` + one hook). Full cross-surface (TUI overlay + alias
editor + Tauri shell) is a multi-slice epic.
- [ ] Architecture decision: backend ownership (proxy vs FCM daemon)
- [ ] Route tool-config URL literals through a shared `getProxyBaseUrl()` (small; 3 literals)
- [ ] Web Request Inspector view (reads `/admin/api/requests`)
- [ ] Alias-table editor (M5 directives) cross-surface + honored by router
- [ ] TUI inspector overlay; Tauri shell (unbuilt)
- [ ] Re-point FCM TUI + web + desktop at FCC admin/stats/health APIs
- [ ] Request Inspector (prompt, routed model + why, tokens, cache, failure cause) — *D4*
- [ ] Replay & A/B compare across models
- [ ] Honest downgrade signaling
- [ ] Tool config-writers target the unified proxy URL

## Milestone 7 — Trust  *(D5)* — data-governance shipped ✅
- [x] `config/provider_policy.py` — per-provider data tags (trains-on-prompts / region;
  local providers = no egress). Best-effort; unknown = conservative.
- [x] `api/data_governor.py` `DataGovernor` — enforces user policy; **HARD exclusion**
  (violating providers dropped entirely, never last-resort — fail rather than leak).
  Unknown data policy treated as non-compliant under a strict setting (fail safe).
- [x] Settings `DATA_REQUIRE_NO_TRAINING` / `DATA_REQUIRE_LOCAL_ONLY` / `DATA_ALLOWED_REGIONS`
  (all opt-in; off by default → no behavior change).
- [x] `RoutingPolicy.order()` hard-filters policy-violating candidates; `classify()` reports
  `policy:<reason>`; empty result → request fails (by design). Admin `GET /admin/api/policy`.
- [x] 20 tests; full suite **1821 passed / 8 skipped** (only no-git fail); ruff+ty+ban clean.
- **Deferred:** egress secret-scrub (touches request/streaming path), per-workspace policy
  (needs client/repo signal — frontend), per-provider trust overrides.
- [ ] Provider data-policy tags (trains-on-prompts? retains? region?)
- [ ] Data-governance routing + per-workspace policy
- [ ] Egress secret-scrub

## Milestone 8 — Deepen the moat  *(D6 + Merge P5/P6)* — M8a/b/c/d shipped ✅
> Response cache (M8a), merged provider catalog / +8 providers (M8b), packaging —
> Docker image + single installer (M8c), and free-tier survival — DROP_TOOLS + auto-fit (M8d,
> live-verified). Deferred: semantic cache + cache-affinity, personalized quality, opt-in
> telemetry, auto self-update (stretch / editor-side / outward-network).

## Milestone 9 — Control Center UI  *(everything visible + configurable from `/admin`)* ✅
> Extended the proxy's loopback admin app (single `freeway` process, no Node dashboard needed).
- [x] **All config UI-editable** — 15 previously-hidden settings surfaced via new manifest
  sections (Routing & Free-tier, Features, Privacy & Data Governance): MODEL_FALLBACKS,
  MODEL_DIRECTIVES, AUTO_FIT_*, DROP_TOOLS, CLAUDE_CODE_AUTO_COMPACT_WINDOW, all ENABLE_*,
  cache window/TTL, data-governance. 133 fields; validate/apply persists to `~/.freeway/.env`.
- [x] **`GET /admin/api/models`** — per-provider aggregation: configured?, health/quota/circuit/
  data-policy status + model list with current/fallback markers.
- [x] **Control-center UI** (`admin.js/index.html/admin.css`): MONITOR tabs — Dashboard,
  Models & Status, Routing/Requests, Quota & Limits, Health, Cache (auto-poll 5s);
  CONFIGURE tabs — Providers, Model Config, Routing, Features, Privacy, Messaging. Models
  view has Set-primary / Add-fallback actions. Observability planes default-ON.
- [x] **Live-verified**: `/admin` + assets 200, all 8 dashboard endpoints 200, config
  validate of new settings valid, `/admin/api/models` returns 26 providers. Full suite
  1906 passed; ruff+ty+node-check clean. Global `freeway` reinstalled with the new UI.
- **Deferred:** per-model latency/SWE-score ranking (would bundle the free-coding-models
  catalog); a "Clear cache" button (needs a small endpoint).

### M8a — opt-in exact-match response cache ✅
- [x] `core/response_cache.py` `ResponseCache` — bounded LRU + TTL over raw
  Anthropic-SSE chunk lists, keyed by request hash; `now` injectable; `snapshot()`
  (entries/hits/misses). Neutral (no api/config imports).
- [x] `capture_and_cache()` tee — commits **only on clean completion** (source fully
  consumed AND `message_stop` seen). Never caches on client disconnect (GeneratorExit),
  cancellation, or mid-stream error → a truncated stream is never replayed forever.
- [x] `api/response_cache_keys.py` — `is_cacheable()` = no tools + explicit
  `temperature == 0` (conservative; default `None` is *not* cacheable);
  `cache_key()` = sha256 of canonical `model_dump` excluding volatile `metadata`/`stream`.
- [x] Wired into `MessagesHandler` (Claude Code path only): cache-check → replay on hit,
  capture-tee on miss. Injected via `get_messages_handler`; `AppRuntime._start_response_cache()`
  gated on `ENABLE_RESPONSE_CACHE`. Admin `GET /admin/api/cache` stats.
- [x] Settings `ENABLE_RESPONSE_CACHE` (default off), `RESPONSE_CACHE_WINDOW` (256),
  `RESPONSE_CACHE_TTL_SECONDS` (300). Off by default → zero behavior change.
- [x] 27 tests (store/TTL/LRU, tee completion+disconnect+error, key policy, handler
  integration, admin endpoint); full suite **1855 passed / 1 skipped** (only no-git fail);
  ruff+ty+ban clean.
- **Deferred:** semantic (near-match) cache + cache-affinity routing; Responses/Chat-completions
  caching (Messages-only for now); personalized quality score (NOT proxy-observable — editor feature).

### M8b — merged provider catalog (union) ✅
- [x] `providers/generic_openai_chat.py` `GenericOpenAIChatProvider` — descriptor-driven
  provider for standard OpenAI `/chat/completions` + Bearer endpoints (default request
  policy, base URL from catalog). One class instead of a bespoke subclass each.
- [x] Mapped 8 providers from the free-coding-models set into the proxy catalog (FCC = routing
  source of truth per merge-plan risk #4): **SambaNova, Novita, OVHcloud, Scaleway, Alibaba
  DashScope, GitHub Models, Ollama Cloud, Routeway** — descriptors + `<id>_api_key`/`<id>_proxy`
  Settings + `.env.example`. Admin manifest, `provider_ids`, quota (`.get()`→none), and
  data-policy (`.get()`→unknown/conservative) are all catalog-derived, so they picked these up
  automatically. Factory registers each via `_make_generic_openai_chat(name)`.
- [x] 41 targeted tests (catalog/factory/build/missing-key + runtime `cases`); order contract
  + admin-manifest contract updated. Full suite **1890 passed / 1 skipped** (only no-git fail);
  ruff+ty+ban clean.
- **Deferred:** no-key gateways **Kilo, LLM7** (need product judgment + can't verify no-auth
  flow locally); model-level catalog stays in FCM `sources.js` (191 models w/ tiers/SWE/ctx —
  not proxy-observable at provider granularity). Per-provider quota limits + data-policy tags
  for the new providers (unknown = conservative today).
### M8c — packaging (Docker + single installer) ✅
- [x] `proxy/Dockerfile` — two-stage uv build on `python:3.14.0-slim` (pinned to
  `.python-version`), non-root `freeway` user with writable `~` for `~/.fcc`, `/health`
  HEALTHCHECK, runtime deps only (no voice/torch). `proxy/.dockerignore`.
  **Built + ran + verified: `GET /health` → 200 `{"status":"healthy"}`, Docker health=healthy.**
- [x] `docker-compose.yml` (top level) — two-process stack: proxy (8082) + frontend (19280),
  `.env` passthrough, frontend points at `http://proxy:8082/v1`. Validated with
  `docker compose config`.
- [x] `scripts/install.sh` + `scripts/install.ps1` — single installer provisioning BOTH
  runtimes (uv sync + corepack pnpm install + vite build). Both syntax/parse-validated.
- [x] `docs/PACKAGING.md` — native + Docker run instructions.
- **Not run:** full `docker compose up` of both services together (frontend image needs
  `web/dist` prebuilt via the installer first; proxy image fully verified standalone).
- **Deferred (rulebook — outward/network, unverifiable locally):** opt-in telemetry,
  auto self-update.
### M8d — free-tier survival: DROP_TOOLS + auto-fit ✅  *(LIVE-verified)*
- [x] `api/tool_filter.py` `DROP_TOOLS` — fnmatch-glob denylist strips tool schemas
  from inbound Messages requests before forwarding (client tools attach every tool's
  full schema to every request; on small free-tier budgets that alone can 413).
- [x] `api/auto_fit.py` `AUTO_FIT_MAX_TOKENS` — when a request exceeds the budget,
  drops the largest **non-essential** tools (largest first) until it fits; keeps the
  core coding tools (`AUTO_FIT_KEEP_TOOLS`). Applied in `MessagesHandler` after DROP_TOOLS.
- [x] `CLAUDE_CODE_AUTO_COMPACT_WINDOW` made configurable (`claude_code_auto_compact_window`).
- [x] **Live E2E** (not just unit tests): real proxy processes + real HTTP + a mock
  upstream that 413s over budget. Same request → **413 with auto-fit off** (reproduced the
  user's exact "Upstream provider … HTTP 413" symptom) → **200 with auto-fit on** (proxy
  auto-dropped Workflow/DesignSync/CronCreate; upstream received 3 tools/1.3k chars vs
  6 tools/36.5k). 20 unit tests + the live run. Full suite **1906 passed / 1 skipped**.
- **Root cause found:** Claude Code's built-in tool schemas (Workflow 21.5k chars, DesignSync,
  Cron*, Task*, …) = 86% of the request, grew via auto-update past Groq's 12k TPM. Not MCP,
  not memory, not fcc injection (all ruled out by capture + code read).
- [ ] Response cache: semantic (near-match) + cache-affinity routing
- [ ] Personalized quality score (accepted/rejected edits per repo/lang)
- [ ] Opt-in telemetry · auto self-update  *(deferred — outward/network)*

## Stretch / moat
- [ ] Community health feed (opt-in, anonymized)
- [ ] Free-tier Autopilot (hands-off best-set assembly)
- [ ] Sub-task planner (true per-word multi-model splitting)

---

**Value order:** M1 → M3 → M4 → M5 deliver the core promise (one resilient,
quota-aware endpoint for every tool + manual override). M6 makes it pleasant,
M7 makes it safe for real code, M8 makes it smarter over time.
