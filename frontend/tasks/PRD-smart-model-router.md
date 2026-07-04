# PRD — Smart Model Router ("FCM Router")

> **Status**: Draft v6 — Phase 6 Onboarding, Install Target & Telemetry implemented — target 0.4.0
> **Author**: Vanessa Depraute + Claude
> **Date**: 2026-04-23
> **Target release**: 0.4.0
> ⚠️ **DO NOT BUMP** — Release only when Vanessa explicitly triggers it after testing.  

---

## 1. Problem Statement

Users of `free-coding-models` currently install individual model endpoints one at a time into their coding tools (OpenCode, OpenClaw, Aider, etc.). When a model goes down, gets rate-limited, or becomes slow, the user has to manually open the TUI, pick a new model, and reinstall the endpoint. This is friction-heavy and interrupts flow.

Meanwhile, the tool already pings 238+ models and knows which ones are healthy in real-time — but that intelligence dies when the TUI closes.

**Goal**: Turn `free-coding-models` from a "model picker" into a **persistent smart router** that automatically keeps users on the best available model at all times — with zero manual intervention after initial setup.

---

## 2. Overview

The FCM Router is a **background daemon** that exposes an OpenAI-compatible API endpoint on localhost. Coding tools connect to this single endpoint instead of individual provider endpoints. The daemon intelligently routes each request to the best healthy model from a user-curated **model set**, handling failover, health monitoring, and circuit breaking transparently.

The TUI gains a new **Router Dashboard** screen for full live monitoring — circuit breaker states, active routing, request logs, and token usage tracking.

### Core Principle

> Install once, code forever. The router adapts — the user doesn't have to.

---

## 2.1 Current Implementation Status

This PRD is now split between **implemented backend foundation** and **remaining product phases**. The first implementation pass landed the daemon and API core, but not the full TUI product experience yet.

### Implemented In Current Branch

| Area | Status | Notes |
|------|--------|-------|
| Daemon lifecycle | ✅ Done | `--daemon`, `--daemon-bg`, `--daemon-status`, and `--daemon-stop` exist. Background daemon uses PID/port files and graceful SIGTERM shutdown. |
| Port discovery | ✅ Done | Daemon prefers `19280`, falls back through `19289`, and writes `~/.free-coding-models-daemon.port`. |
| Logging | ✅ Done | Writes `~/.free-coding-models-daemon.log` with 5 MB rotation and `error/warn/info/debug` levels. |
| Router config schema | ✅ Done | `router` config is normalized and preserved by `src/config.js`; unrelated config saves no longer drop router data. |
| Default router set | ✅ Done | First daemon start auto-creates `fast-coding` from configured providers, falling back to top catalog models if no keys exist. |
| Config + env API keys | ✅ Done | Daemon reads config keys first and environment variables as fallback; config reload runs every 60s. |
| OpenAI-compatible reverse proxy | ✅ Done | `/v1/chat/completions` rewrites URL, auth header, and `model`; request body fields are otherwise passed through. |
| Named set endpoint | ✅ Done | `/v1/sets/:name/chat/completions` routes through a named set. |
| Virtual model list | ✅ Done | `/v1/models` returns `fcm` and `fcm:<set-name>` virtual models. |
| Set API backend | ✅ Done | Backend supports `GET /sets`, `POST /sets`, `PUT /sets/:name`, `DELETE /sets/:name`, and `POST /sets/:name/activate`. |
| Health probes | ✅ Backend done | Cold-start burst, rolling probe windows, staggered steady probing, Eco/Balanced/Aggressive intervals. |
| Circuit breaker | ✅ Backend done | CLOSED / HALF_OPEN / OPEN states, exponential cooldown, auth errors separated from transient failures. |
| Scoring | ✅ Backend done | Score uses latency, uptime, and user priority. Cold start falls back to priority order. |
| Request failover | ✅ Backend done | Non-streaming failover, streaming failover before first byte, timeout failover, connection-refused failover, HTML maintenance-page failover, and malformed JSON failover are implemented. Partial streamed responses are not retried after bytes are sent. |
| Stale model detection | ✅ Backend done | Set entries missing from `sources.js` are marked stale and skipped. |
| Stats endpoints | ✅ Done | `/health`, `/stats`, `/stats/tokens`, `/stats/tokens/daily/:date`, and `/stream/events` exist. |
| Token tracking | ✅ Partial | Non-streaming OpenAI `usage` fields are tracked daily/all-time. Streaming token extraction is still not tracked. |
| SSE events | ✅ Backend done | Emits `request`, `probe`, `circuit`, and `set_change` events. No TUI consumer yet. |
| Telemetry | ✅ Backend done | Daemon start/stop, failover, circuit-open, all-down, router-error, and external-restart-trigger telemetry are wired. |
| Upstream hardening | ✅ Backend done | Client disconnect aborts, quota metadata extraction, same-provider auth skipping, HTML detection, malformed JSON detection, and restart endpoint removal are implemented. |
| Tests | ✅ Done | Unit coverage plus fake-upstream router integration coverage for success routing, failover, streaming behavior, auth errors, all-down `503`, malformed upstream responses, timeouts, connection refused, and client disconnects. |
| Documentation | ✅ Done | README, flags docs, config docs, changelog, and this PRD reflect the current router foundation. |

### Not Implemented Yet

| Area | Status | Why it matters |
|------|--------|----------------|
| Router Dashboard TUI | ✅ Done | `Shift+R` opens a full-screen TUI dashboard backed by `/health`, `/stats`, and `/stream/events`; it renders daemon state, active set, port, uptime, probe mode, model health/circuit state, token totals, and the live request log. |
| Set Manager TUI | ✅ Done | `Shift+S` opens two-pane Set Manager; N/D/R/⌫/A actions, Tab pane switching, model reorder via Shift+↑/↓ |
| Position picker | ✅ Done | `Shift+A` opens position picker; ↑↓ to select insertion point, Enter to confirm, Esc to cancel |
| Main TUI router footer/status | ✅ Done | Footer shows `● Router: <set> Today: Ntok All-time: Ntok` when daemon running; `○ Router: daemon not running` otherwise |
| Token Usage screen | ✅ Done | `Shift+T` fetches `/stats/tokens`, renders today/all-time breakdowns, top models today with bar chart, and 7-day history chart |
| Onboarding overlay/banner | ✅ Done | New users see enable prompt; existing users see upgrade banner (10s TTL). |
| `FCM Router` install target | ✅ Done | Added to `INSTALL_TARGET_MODES`; installs provider into daemon via `/sets/:name` PUT. |
| Auto-start on boot | ❌ Not started | No launchd/systemd setup or Settings toggle yet. |
| Command palette router actions | ✅ Done | Ctrl+P includes Router Dashboard (Shift+R), Router Sets (Shift+S), and Token Usage (Shift+T) entries |
| Full npm release verification | ❌ Not done | Implementation was tested locally, but no version bump, publish, or global npm tarball verification was performed. |
| `app_router_install` telemetry | ✅ Done | Fires when user successfully enables router from onboarding. |
| `app_router_use` telemetry | ✅ Done | Fires every 10th routed request with total_requests + active_set. |

### Current Usable Slice

Users can manually start the router and configure tools by hand:

```bash
free-coding-models --daemon-bg
free-coding-models --daemon-status
```

Tool config:

| Field | Value |
|-------|-------|
| Base URL | `http://localhost:19280/v1` |
| Model | `fcm` |
| API key | `fcm-local` |

This is enough to validate the backend router behavior before building the full TUI/dashboard UX.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Coding Tool                          │
│  (OpenCode, Aider, Cline, Goose, etc.)                  │
│  base_url: http://localhost:19280/v1                    │
│  model: "fcm"                                           │
└──────────────────────┬──────────────────────────────────┘
                       │ OpenAI-compatible request
                       ▼
┌─────────────────────────────────────────────────────────┐
│              FCM Router Daemon (background)              │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Health Probe │  │ Circuit      │  │ Request        │  │
│  │ Engine       │  │ Breaker      │  │ Interceptor    │  │
│  │ (30s cycle)  │  │ (per-model)  │  │ (stream-aware) │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │           │
│         ▼                ▼                   ▼           │
│  ┌──────────────────────────────────────────────────┐    │
│  │            Scoring & Routing Engine               │    │
│  │  score = f(latency, uptime, user_priority)        │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │ Token Tracker │  │ Set Manager  │                      │
│  │ (per-model)   │  │ (multi-set)  │                      │
│  └──────────────┘  └──────────────┘                      │
│                                                          │
│  Endpoints:                                              │
│    /v1/chat/completions    → active set routing           │
│    /v1/models              → virtual model list           │
│    /v1/sets/:name/chat/completions → named set routing    │
│    /health                 → daemon status JSON           │
│    /stats                  → token usage + routing stats  │
└──────────────────────────────────────────────────────────┘
                       │
                       ▼ (routes to best healthy model)
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ NVIDIA   │  │ Groq     │  │ Cerebras │  ...
   │ NIM      │  │          │  │          │
   └──────────┘  └──────────┘  └──────────┘
```

### 3.1 Daemon Process

- **Lifecycle**: Spawned as a detached child process (`child_process.fork` with `detached: true, stdio: 'ignore'`). Survives TUI closure. Always the same version as the TUI — they are the same package, the TUI spawns the daemon.
- **PID file**: `~/.free-coding-models-daemon.pid` — used for TUI reconnection and cleanup.
- **Port**: Fixed default `19280`, with automatic fallback to next available port if occupied. Port written to `~/.free-coding-models-daemon.port` for discovery.
- **Port discovery**: If the TUI can't connect to the expected port, it reads the `.port` file. If that also fails, it scans a small port range (`19280-19289`) before declaring the daemon unreachable.
- **Auto-restart**: If TUI detects the daemon is dead (PID file exists but process gone), it respawns automatically.
- **Graceful shutdown**: On SIGTERM, the daemon finishes in-flight requests (up to 30s timeout), writes final stats to disk, then exits.

#### CLI Flags

| Flag | Description |
|------|-------------|
| `--daemon` | Start the router daemon in foreground (for launchd/systemd) |
| `--daemon-bg` | Start the daemon in background (detached). Used internally by the TUI |
| `--daemon-stop` | Send SIGTERM to the running daemon (reads PID from `.pid` file) |
| `--daemon-status` | Print daemon status JSON to stdout and exit |

#### Logging

The daemon writes logs to `~/.free-coding-models-daemon.log`:
- **Rotation**: Max 5 MB, 2 rotated files (`.log` + `.log.1`)
- **Levels**: `error`, `warn`, `info` (default), `debug` (activate via `router.logLevel: "debug"` in config)
- **Format**: `[ISO8601] [LEVEL] message` — e.g., `[2026-04-22T10:42:15Z] [INFO] Routed to groq/llama-3.3-70b — 182ms`
- **What's logged**: Daemon start/stop, routing decisions, failovers, circuit breaker transitions, probe results (info level). Full request headers/errors at debug level. Never logs request/response bodies.

### 3.2 API Key Management

The daemon needs real API keys to forward requests to providers. It reads them from **two sources**, in order of precedence:

1. **Config file** (`~/.free-coding-models.json`) — keys stored via the Settings screen (P key). This is the primary source and the only one that works with auto-start on boot.
2. **Environment variables** (`GROQ_API_KEY`, `NVIDIA_API_KEY`, etc.) — inherited from the TUI process at fork time. Used as fallback if the config file doesn't have a key for a provider.

The daemon re-reads the config file every 60s to pick up new keys added via Settings without requiring a daemon restart.

### 3.3 Reverse Proxy — Request Rewriting

The daemon acts as a transparent reverse proxy. When a coding tool sends a request to `http://localhost:19280/v1/chat/completions`, the daemon rewrites it before forwarding:

```
INCOMING (from tool)                    OUTGOING (to provider)
─────────────────────                   ──────────────────────
POST /v1/chat/completions               POST /v1/chat/completions
Host: localhost:19280                    Host: api.groq.com
Authorization: Bearer fcm-local         Authorization: Bearer gsk_xxx...
{ "model": "fcm", ... }                 { "model": "llama-3.3-70b-versatile", ... }
```

Three fields are rewritten:
1. **URL** → provider's base URL (from `sources.js` provider config)
2. **Authorization header** → real API key (from config file or env var)
3. **model field in body** → actual model ID at that provider

Everything else (messages, temperature, stream, tools, etc.) is passed through untouched. The response is streamed back to the tool as-is — the `model` field in the response will contain the real model name (not "fcm"), which is fine and actually useful for debugging.

### 3.4 Communication: TUI ↔ Daemon

The TUI communicates with the daemon via **HTTP on localhost**:
- `GET /health` — daemon alive check + current state summary
- `GET /stats` — token counts, routing stats, circuit breaker states
- `POST /sets` — CRUD operations on model sets
- `POST /sets/:name/activate` — switch active set
- `GET /stream/events` — SSE (Server-Sent Events) stream for live dashboard updates (new requests, state changes, health probes)

Configuration is persisted in `~/.free-coding-models.json` under a `router` key — same config file as the rest of the app, keeping everything centralized.

---

## 4. Feature Specifications

### 4.1 Model Sets

A **set** is a named, ordered list of models with routing metadata.

#### Data Model

```json
{
  "router": {
    "enabled": true,
    "activeSet": "fast-coding",
    "sets": {
      "fast-coding": {
        "name": "fast-coding",
        "models": [
          { "provider": "groq", "model": "llama-3.3-70b-versatile", "priority": 1 },
          { "provider": "cerebras", "model": "llama-3.3-70b", "priority": 2 },
          { "provider": "sambanova", "model": "DeepSeek-V3-0324", "priority": 3 }
        ],
        "created": "2026-04-22T10:00:00Z"
      },
      "deep-reasoning": {
        "name": "deep-reasoning",
        "models": [
          { "provider": "nvidia", "model": "deepseek-ai/deepseek-r1", "priority": 1 },
          { "provider": "openrouter", "model": "deepseek/deepseek-r1", "priority": 2 }
        ],
        "created": "2026-04-22T10:05:00Z"
      }
    }
  }
}
```

#### Set Management Operations

| Operation | Description |
|-----------|-------------|
| Create set | Name a new set, starts empty |
| Add model to set | From main table — pick position (priority) via up/down reorder UI |
| Remove model from set | Remove from the active or any named set |
| Reorder models | Move up/down within a set to change priority |
| Rename set | Change the display name |
| Delete set | Remove entirely (with confirmation) |
| Duplicate set | Clone an existing set as starting point |
| Switch active set | Change which set the daemon routes to |

#### Set Management UI (dedicated overlay)

Accessed from the main TUI via a **Shift combo** (see §6 Keybindings). Opens a full-screen overlay with:

- **Left pane**: List of all sets (highlighted = active)
- **Right pane**: Models in the selected set, ordered by priority
- **Inline actions**: 
  - Arrow keys to navigate
  - Enter to select/expand
  - Up/Down + modifier to reorder priority within a set
  - Delete/Backspace to remove
  - Type to search/filter when adding models

When adding a model to a set from the main table, a **position picker** appears: the user sees the current set members and uses arrow keys to place the new model at the desired priority position before confirming.

### 4.2 Smart Routing Engine

#### 4.2.1 Health Probe Engine

Runs continuously in the daemon, independent of any active requests.

##### Probe Modes

The probe engine supports **3 intensity presets** configurable from the Router Dashboard (key `I`):

| Mode | Probe interval | Token cost | Best for |
|------|---------------|------------|----------|
| **Eco** | 120s | ~0.5 tok/probe (HEAD-only where supported, `max_tokens: 1` fallback) | Low-cap providers (OpenRouter 50 req/day), overnight idle |
| **Balanced** (default) | 30s | ~1 tok/probe (`max_tokens: 1`) | Normal usage |
| **Aggressive** | 10s | ~1 tok/probe (`max_tokens: 1`) | Active coding sessions, need fastest failover |

**Eco mode detail**: For providers that support `HEAD /v1/models` or `GET /v1/models` (most do — see `PROVIDER_AUTH_ENDPOINTS` in `key-handler.js`), eco mode uses a **zero-token health check** — it calls the models endpoint instead of chat completions. This confirms the API key works and the provider is reachable without consuming any tokens. For providers without a models endpoint (e.g., Cloudflare), it falls back to `max_tokens: 1`.

##### Probe Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Probe method (balanced/aggressive) | `POST /chat/completions` | `{ model, messages: [{ role: "user", content: "hi" }], max_tokens: 1, stream: false }` |
| Probe method (eco) | `GET /v1/models` or `HEAD` | Zero-token availability check; falls back to `max_tokens: 1` if no models endpoint |
| Probe timeout | 10s | Shorter than normal request timeout |
| Stagger | Probes spread across the interval | Avoids burst-pinging all models simultaneously |
| Data collected | latency_ms, http_status, quota_remaining (from headers) | Stored in rolling window (last 20 probes per model) |

##### Cold Start Behavior

When the daemon starts, rolling windows are empty — no latency or uptime data exists yet. Cold start sequence:

1. **Immediate burst**: On startup, the daemon fires one probe to every model in the active set simultaneously (not staggered). This takes ~10s max (probe timeout).
2. **First request routing**: If a request arrives before the burst completes, routing falls back to **pure user priority order** — model at priority 1 is tried first, then 2, etc.
3. **Transition to steady state**: After the initial burst, the daemon switches to the configured probe mode (Eco/Balanced/Aggressive) with normal stagger.

This means the daemon is usable within seconds of starting, and fully scored within ~10s.

##### Probe Monitoring (visible in Dashboard)

The dashboard displays probe activity in the header section:

```
Probes: Balanced (30s)  │  Cost: ~2.1K tok/day  │  12 probes/min  │  Last: 3s ago
```

| Metric | Description |
|--------|-------------|
| Mode label | Current probe intensity (Eco / Balanced / Aggressive) |
| Estimated cost | Rolling daily token estimate based on probe frequency × models in set |
| Probe rate | Actual probes per minute (accounts for stagger and retries) |
| Last probe | Time since last probe completed |

#### 4.2.2 Circuit Breaker (per-model)

Three states:

```
CLOSED (healthy) ──[3 consecutive failures]──► OPEN (broken, skip)
      ▲                                              │
      │                                    [cooldown expires]
      │                                              ▼
      └────────[1 success]──── HALF_OPEN (testing) ──┘
                                     │
                               [1 failure]
                                     │
                                     ▼
                              OPEN (reset cooldown)
```

| Parameter | Value |
|-----------|-------|
| Failure threshold | 3 consecutive failures |
| Initial cooldown | 30s |
| Backoff multiplier | 2x |
| Max cooldown | 5 minutes |
| What counts as failure | HTTP 429, 500, 502, 503, timeout, connection refused |

**Important**: HTTP 401/403 (auth errors) do **not** trigger the circuit breaker — they indicate a configuration problem, not a transient failure. These are flagged as `AUTH_ERROR` in the dashboard so the user can fix their API key.

#### 4.2.3 Scoring Algorithm

Each model in the active set gets a dynamic score recalculated after every health probe:

```
score = (0.4 × latency_score) + (0.4 × uptime_score) + (0.2 × priority_bonus)

where:
  latency_score  = 1 - (p95_latency / max_p95_in_set)     // 0..1, lower latency = higher
  uptime_score   = successful_probes / total_probes         // 0..1, from rolling window
  priority_bonus = 1 - ((user_priority - 1) / set_size)    // 0..1, priority 1 = highest bonus
```

The daemon routes to the **highest-scoring model with a CLOSED circuit breaker**. If all CLOSED models are exhausted, it tries HALF_OPEN models in score order.

#### 4.2.4 Request-Level Failover (Stream-Aware)

This is the real-time safety net when routing an actual user request:

1. Daemon receives request from coding tool
2. Forwards to highest-scoring healthy model
3. **Non-streaming**: If response is error (429/5xx) or timeout (15s) → immediately retry on next model
4. **Streaming**: 
   - If initial connection fails → retry on next model (transparent)
   - If stream starts but **stalls** (no chunk received for 8s) → abort, retry on next model
   - If stream has already sent data to the client → cannot transparently retry (partial response). Log the failure, update circuit breaker, but let the partial response through. The next request will route to the healthier model.
5. **Max retries**: Try up to 3 different models per request. After 3 failures → return `503` with clear error message.

**Transparency guarantee**: For non-streaming and for streaming before first byte — the coding tool never sees the failure. It just experiences slightly higher latency from the retry.

### 4.3 Multi-Endpoint Routing

The daemon exposes multiple routing endpoints for different use cases:

| Endpoint | Routes via | Use case |
|----------|-----------|----------|
| `/v1/chat/completions` | Active set | Default — install this in your tool |
| `/v1/sets/:setName/chat/completions` | Named set | Advanced — different tools use different sets |
| `/v1/models` | Returns virtual model list | Tool compatibility (lists `"fcm"` + set names) |

**Example**: A user could configure OpenCode to use the `fast-coding` set and Aider to use the `deep-reasoning` set, simultaneously:
- OpenCode: `base_url: http://localhost:19280/v1/sets/fast-coding`
- Aider: `base_url: http://localhost:19280/v1/sets/deep-reasoning`

The `/v1/models` endpoint returns:
```json
{
  "data": [
    { "id": "fcm", "object": "model", "owned_by": "fcm-router" },
    { "id": "fcm:fast-coding", "object": "model", "owned_by": "fcm-router" },
    { "id": "fcm:deep-reasoning", "object": "model", "owned_by": "fcm-router" }
  ]
}
```

Tools send `model: "fcm"` (or `model: "fcm:set-name"`) — the daemon ignores the model field for the default endpoint, or extracts the set name for named endpoints.

### 4.4 Token Usage Tracking

The daemon reads the `usage` field from every successful response:

```json
{
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 340,
    "total_tokens": 490
  }
}
```

#### Storage

Token counts are persisted in `~/.free-coding-models-tokens.json`:

```json
{
  "daily": {
    "2026-04-22": {
      "total_tokens": 48500,
      "prompt_tokens": 18200,
      "completion_tokens": 30300,
      "requests": 42,
      "by_model": {
        "groq/llama-3.3-70b-versatile": { "total": 25000, "requests": 28 },
        "cerebras/llama-3.3-70b": { "total": 23500, "requests": 14 }
      }
    }
  },
  "all_time": {
    "total_tokens": 2450000,
    "prompt_tokens": 980000,
    "completion_tokens": 1470000,
    "requests": 1847,
    "first_tracked": "2026-04-22T10:00:00Z"
  }
}
```

#### Retention

- **Daily granularity**: Last 90 days kept, older entries pruned automatically.
- **All-time counters**: Never reset (unless user manually clears).
- **File writes**: Batched every 60s to avoid disk thrashing. In-memory accumulator with flush-on-shutdown.

### 4.5 Router Dashboard (TUI Screen)

A full-screen TUI overlay accessed via keybinding, providing live monitoring of the daemon.

#### Layout

```
╔══════════════════════════════════════════════════════════════════════╗
║  FCM Router Dashboard          Set: fast-coding ▸  Port: 19280     ║
║  Daemon: ● RUNNING   Uptime: 2h 14m   Requests routed: 247        ║
║  Probes: Balanced (30s)  │  Cost: ~2.1K tok/day  │  Last: 3s ago   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  MODEL HEALTH                              TOKEN USAGE              ║
║  ┌──────────────────────────────────────┐  ┌──────────────────────┐ ║
║  │ # Provider   Model        State  Ms │  │ Today     148.2K tok │ ║
║  │ 1 groq       llama-3.3-70 ● OK  180 │  │ All-time  2.45M tok  │ ║
║  │ 2 cerebras   llama-3.3-70 ● OK  220 │  │ Requests  247 today  │ ║
║  │ 3 sambanova  DeepSeek-V3  ◐ HALF 1s │  │ Total req 1,847      │ ║
║  │ 4 nvidia     deepseek-r1  ○ OPEN  — │  │                      │ ║
║  └──────────────────────────────────────┘  │ Top model today:     │ ║
║                                            │ groq/llama → 98.2K   │ ║
║  LIVE REQUEST LOG                          └──────────────────────┘ ║
║  ┌──────────────────────────────────────────────────────────────────┐║
║  │ 10:42:15  groq/llama-3.3    ✓ 200  182ms   490 tok             │║
║  │ 10:42:08  groq/llama-3.3    ✓ 200  195ms   1.2K tok            │║
║  │ 10:41:55  cerebras/llama    ✓ 200  240ms   380 tok  (failover) │║
║  │ 10:41:55  groq/llama-3.3    ✗ 429    —       —      rate-limit │║
║  │ 10:41:30  groq/llama-3.3    ✓ 200  178ms   820 tok             │║
║  │ 10:41:12  groq/llama-3.3    ✓ 200  190ms   2.1K tok            │║
║  └──────────────────────────────────────────────────────────────────┘║
║                                                                     ║
║  [S] Switch set  [I] Probe mode  [R] Restart  [C] Clear  [Esc] Back ║
╚══════════════════════════════════════════════════════════════════════╝
```

#### Dashboard Features

| Section | Content | Update frequency |
|---------|---------|-----------------|
| **Header** | Active set name, daemon port, running status, uptime, total requests | Real-time via SSE |
| **Model Health** | Each model in active set: priority, provider, model name, circuit breaker state (● CLOSED / ◐ HALF_OPEN / ○ OPEN), last probe latency | Every probe (30s) |
| **Token Usage** | Today's tokens, all-time tokens, request counts, top model by usage | Every request |
| **Live Request Log** | Last 20 requests: timestamp, model used, HTTP status, latency, token count, failover indicator | Every request |

#### Circuit Breaker Visual States

| Symbol | State | Color | Meaning |
|--------|-------|-------|---------|
| `●` | CLOSED | Green | Healthy, actively routing |
| `◐` | HALF_OPEN | Yellow | Recovery probe pending |
| `○` | OPEN | Red | Broken, skipped until cooldown |
| `⚠` | AUTH_ERROR | Magenta | API key issue — needs user action |
| `💀` | STALE | Gray | Model no longer in sources — skipped |

### 4.6 Main TUI Status Indicator

When the daemon is running, the main table's footer bar shows a persistent status line:

```
🔀 Router: ● fast-coding (4 models)  │  Today: 148.20K tok  │  All-time: 2.45M tok
```

| Element | Description |
|---------|-------------|
| `🔀 Router:` | Fixed label — always visible when router is enabled |
| `●` / `○` | Green dot = daemon running, red dot = daemon down |
| `fast-coding (4 models)` | Active set name and model count |
| `Today: 148.20K tok` | Tokens consumed today, formatted with 2 decimals in K/M |
| `All-time: 2.45M tok` | Total tokens since first tracked, formatted with 2 decimals in K/M |

When the router is disabled, this line is hidden entirely — no wasted space.

Token formatting rules:
- `< 1,000` → raw number: `847 tok`
- `1,000 – 999,999` → K with 2 decimals: `148.20K tok`
- `≥ 1,000,000` → M with 2 decimals: `2.45M tok`

### 4.7 Stale Model Detection

Models in a set can become **stale** when they are removed from `sources.js` (provider drops support, model deprecated, etc.).

On daemon startup and every config re-read (60s), the daemon cross-references set models against the current `sources.js` model list:

- **Model still exists in sources** → normal routing
- **Model NOT found in sources** → marked as `STALE`

Stale models:
- Are **skipped during routing** (never receive traffic)
- Show `💀 STALE` in the Router Dashboard (distinct from OPEN/AUTH_ERROR)
- Are **not removed automatically** from the set — the user might want to keep them in case the model comes back
- Generate a **one-time notification** in the dashboard: `"⚠ groq/old-model-id is no longer available and will be skipped"`

### 4.8 Daemon Activation & Onboarding

#### New Users (first launch)

On first `free-coding-models` launch (detected by `config.router` not existing):

1. After initial ping results load, show an **onboarding overlay**:
   ```
   ┌─────────────────────────────────────────────┐
   │  🚀 Smart Router Available!                  │
   │                                              │
   │  FCM can run a background daemon that        │
   │  automatically routes your requests to the   │
   │  fastest healthy model — with zero config.   │
   │                                              │
   │  • Auto-failover when models go down         │
   │  • Circuit breaker prevents slow routing     │
   │  • Token usage tracking                      │
   │                                              │
   │  Enable the Smart Router?                    │
   │                                              │
   │  [Y] Yes, enable    [N] Not now    [?] Learn │
   └─────────────────────────────────────────────┘
   ```
2. If **Yes**: daemon starts, a default set is auto-created from the top 5 healthy models currently visible, user is shown the Router Dashboard briefly.
3. If **Not now**: `config.router.enabled = false`, `config.router.onboardingSeen = true`. User can enable later from Settings.

#### Existing Users (upgrade)

On first launch after upgrading to a version with the router:

1. Detect `config.router === undefined` AND `config.favorites` or other keys exist (proves not first launch).
2. Show a **non-blocking notification banner** at the top of the TUI for 10 seconds:
   ```
   ┌──────────────────────────────────────────────────────────────────┐
   │  🆕 Smart Router is now available! Press Shift+R to set it up.  │
   └──────────────────────────────────────────────────────────────────┘
   ```
3. Pressing Shift+R opens the same onboarding overlay.
4. After dismissal (or 10s timeout), set `config.router.onboardingSeen = true` so it doesn't show again.

### 4.9 Tool Installation

When the router is enabled, the existing "install endpoint" flow gains a new option.

Currently, pressing Enter on a model installs that specific model's endpoint into the selected tool. With the router:

1. A new install target appears: **"FCM Router"** at the top of the tool list.
2. Selecting it writes:
   - `base_url`: `http://localhost:19280/v1` (or `/v1/sets/:name` for named sets)
   - `model`: `"fcm"`
   - `api_key`: `"fcm-local"` (dummy — the daemon handles real keys)
3. The tool now routes all requests through the daemon.

This coexists with direct model installs — users can still install individual models directly if they prefer.

---

## 5. Token Usage Screen

Separate from the Router Dashboard, a **Token Usage** screen provides historical views.

#### Layout

```
╔══════════════════════════════════════════════════════════════════════╗
║  Token Usage                                                        ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  TODAY (2026-04-22)                    ALL TIME                      ║
║  ───────────────────                   ────────                      ║
║  Total tokens:   148,200               Total tokens:   2,450,000    ║
║  Prompt tokens:   55,800               Prompt tokens:    980,000    ║
║  Completion:      92,400               Completion:     1,470,000    ║
║  Requests:            42               Requests:           1,847    ║
║                                        Since: 2026-04-22            ║
║                                                                     ║
║  TODAY BY MODEL                                                     ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  groq/llama-3.3-70b-versatile      98,200 tok   28 req  66% │   ║
║  │  cerebras/llama-3.3-70b            35,400 tok   10 req  24% │   ║
║  │  sambanova/DeepSeek-V3-0324        14,600 tok    4 req  10% │   ║
║  └──────────────────────────────────────────────────────────────┘   ║
║                                                                     ║
║  LAST 7 DAYS                                                        ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  Mon  ████████████████████████░░░░░░░░  148K                │   ║
║  │  Sun  ██████████████████░░░░░░░░░░░░░░  112K                │   ║
║  │  Sat  ████████████░░░░░░░░░░░░░░░░░░░░   78K                │   ║
║  │  Fri  ██████████████████████████░░░░░░  185K                │   ║
║  │  Thu  ████████████████████░░░░░░░░░░░░  134K                │   ║
║  │  Wed  ██████████████░░░░░░░░░░░░░░░░░░   95K                │   ║
║  │  Tue  ████████████████████████████░░░░  201K                │   ║
║  └──────────────────────────────────────────────────────────────┘   ║
║                                                                     ║
║  [Esc] Back                                                         ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 6. Keybindings

Since all single-letter keys (A-Z) are already assigned, the router uses **Shift combos** for global access and **local keys** within the router screens.

### Global Keys (main table)

| Key | Action |
|-----|--------|
| `Shift+R` | Open Router Dashboard |
| `Shift+S` | Open Set Manager overlay |
| `Shift+A` | Add selected model to a set (opens position picker) |
| `Shift+T` | Open Token Usage screen |

### Router Dashboard Keys (local to dashboard screen)

| Key | Action |
|-----|--------|
| `S` | Switch active set |
| `R` | Restart daemon |
| `C` | Clear request log |
| `P` | Pause/resume health probes |
| `I` | Cycle probe intensity (Eco → Balanced → Aggressive) |
| `Esc` | Back to main table |

> Phase 3 note: `R` and `P` intentionally show disabled/reserved notices until Phase 7 adds service-manager restart support and the backend gains probe pause/resume semantics. Detailed/compact dashboard view can be added later if the screen becomes too dense.

### Set Manager Keys (local to set manager overlay)

| Key | Action |
|-----|--------|
| `N` | New set |
| `D` | Duplicate selected set |
| `R` | Rename selected set |
| `Delete` / `Backspace` | Remove model or delete set (with confirm) |
| `Shift+Up` / `Shift+Down` | Reorder model priority within set |
| `Enter` | Expand set / select model |
| `A` | Activate selected set for the daemon |
| `Tab` | Switch focus between left pane (sets) and right pane (models) |
| `Esc` | Back to main table |

### Position Picker Keys (when adding model to set via Shift+A)

| Key | Action |
|-----|--------|
| `Up` / `Down` | Move insertion point |
| `Enter` | Confirm position |
| `Esc` | Cancel |

---

## 7. Configuration Schema

All router config lives in `~/.free-coding-models.json` under the `router` key:

```json
{
  "router": {
    "enabled": true,
    "onboardingSeen": true,
    "autoStartOnBoot": false,
    "port": 19280,
    "activeSet": "fast-coding",
    "sets": { "...": "see §4.1" },
    "probeMode": "balanced",
    "probeIntervals": {
      "eco": 120000,
      "balanced": 30000,
      "aggressive": 10000
    },
    "circuitBreaker": {
      "failureThreshold": 3,
      "initialCooldownMs": 30000,
      "maxCooldownMs": 300000,
      "backoffMultiplier": 2
    },
    "failover": {
      "maxRetries": 3,
      "streamStallTimeoutMs": 8000,
      "requestTimeoutMs": 15000
    },
    "scoring": {
      "latencyWeight": 0.4,
      "uptimeWeight": 0.4,
      "priorityWeight": 0.2
    }
  }
}
```

All values have sensible defaults — zero config required for the basic use case.

**Note on `probeMode`**: Controls both the probe interval AND the probe method. In `"eco"` mode, the daemon prefers zero-token health checks (GET `/v1/models`) over chat completions. Users can override individual interval values in `probeIntervals` but the mode string is the recommended way to switch.

---

## 8. API Reference (Daemon HTTP Endpoints)

### Public Endpoints (used by coding tools)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat/completions` | Route request via active set |
| `POST` | `/v1/sets/:name/chat/completions` | Route request via named set |
| `GET` | `/v1/models` | List virtual models (for tool compatibility) |

### Internal Endpoints (used by TUI)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Daemon status, active set, port, uptime |
| `GET` | `/stats` | Token usage, routing stats, per-model breakdown |
| `GET` | `/stats/tokens` | Token usage only (today + all-time) |
| `GET` | `/stats/tokens/daily/:date` | Token usage for a specific day |
| `GET` | `/stream/events` | SSE stream for live dashboard updates |
| `GET` | `/sets` | List all sets |
| `POST` | `/sets` | Create a new set |
| `PUT` | `/sets/:name` | Update set (reorder, add/remove models) |
| `DELETE` | `/sets/:name` | Delete a set |
| `POST` | `/sets/:name/activate` | Switch daemon to this set |
| `POST` | `/daemon/shutdown` | Graceful shutdown |

### SSE Event Types (`/stream/events`)

| Event | Payload | When |
|-------|---------|------|
| `request` | `{ model, status, latency_ms, tokens, failover }` | Every routed request |
| `probe` | `{ model, status, latency_ms, circuit_state }` | Every health probe |
| `circuit` | `{ model, old_state, new_state, cooldown_ms }` | Circuit breaker state change |
| `set_change` | `{ old_set, new_set }` | Active set switched |

---

## 9. Edge Cases & Error Handling

| Scenario | Behavior |
|----------|----------|
| All models in set are OPEN | Return `503 { error: "All models in set are unavailable", set: "fast-coding", models_tried: [...] }`. If any model was skipped due to quota exhaustion (429 with rate-limit headers showing 0 remaining), include `"quota_exhausted": ["groq/llama-3.3-70b"]` plus `"quota_exhausted_details"` with retry/rate-limit metadata so the user knows *why* and can switch to a set with different providers |
| Daemon port occupied on start | Try ports 19280→19289 sequentially, write actual port to `.port` file |
| TUI can't find daemon | Check PID file → check .port file → scan 19280-19289 → offer to restart |
| Streaming: partial response then failure | Let partial response through (can't un-send bytes), log failure, update circuit breaker. Next request routes to healthier model |
| API key missing for a provider in set | Mark model as `AUTH_ERROR` (not circuit-broken). Show ⚠ in dashboard. Skip during routing but don't count as failure |
| Provider returns `401`/`403` during a request | Mark that model as `AUTH_ERROR`, skip remaining candidates from the same provider for this request, and try the next provider if one is available |
| Client disconnects mid-request | Abort the upstream fetch and stop work without counting it as a provider failure |
| Config file locked/corrupted | Daemon keeps running with in-memory state. TUI shows warning. Retry config write on next interval |
| User deletes the active set | Fall back to first available set. If no sets exist, pause daemon and notify user |
| Token file grows too large | Auto-prune daily entries older than 90 days on daemon startup |
| Concurrent TUI instances | Multiple TUIs can connect to the same daemon via SSE. Set changes from any TUI are reflected in all |
| Model removed from sources.js | Mark as `STALE` (💀) in dashboard, skip during routing, keep in set. Notify user once |
| Daemon started via auto-start (no env vars) | Reads API keys exclusively from config file. If key missing → `AUTH_ERROR` for that model. User must configure keys via Settings |

---

## 10. Error Handling & Zero-Crash Guarantees

The daemon is a long-running background process. It must **never crash**. Every error is caught, logged, and recovered from — the worst outcome is a degraded response, never a dead process.

### 10.1 Process-Level Protection

```js
// 📖 Top-level safety net — these are the last line of defense.
// 📖 Any error that reaches here is a bug, but the daemon must survive.
process.on('uncaughtException', (err) => { /* log, do NOT exit */ })
process.on('unhandledRejection', (reason) => { /* log, do NOT exit */ })
```

| Scenario | Behavior |
|----------|----------|
| Uncaught exception | Log full stack trace at `error` level. Do **not** exit for ordinary isolated exceptions. Increment a `crash_recovered` counter exposed in `/health`. If 10+ uncaught exceptions happen in 5 minutes, gracefully shut down with exit code `1` so launchd/systemd or the future TUI service manager can restart it; the daemon does not self-spawn a second process from inside the same process. |
| Unhandled promise rejection | Same as uncaught exception — log and continue |
| Out of memory (heap) | Node.js will kill the process regardless. PID file becomes stale → TUI auto-restarts daemon on next connect. To prevent OOM: all rolling windows, logs, and caches have hard caps (see §10.5) |
| SIGTERM | Graceful shutdown: stop accepting new requests, drain in-flight (30s max), flush token stats, delete PID file, exit 0 |
| SIGINT | Same as SIGTERM |
| SIGHUP | Re-read config file (hot reload API keys, probe mode, sets) without restarting |

### 10.2 HTTP Server Errors

The daemon's HTTP server must handle every possible input gracefully.

| Scenario | Response | Log level |
|----------|----------|-----------|
| Malformed JSON body | `400 { "error": "Invalid JSON", "detail": "Unexpected token at position 42" }` | warn |
| Missing `model` field in body | `400 { "error": "Missing required field: model" }` | warn |
| Unknown route (e.g., `POST /v2/foo`) | `404 { "error": "Not found" }` | info |
| Request body too large (>10 MB) | `413 { "error": "Request body too large", "max_bytes": 10485760 }` | warn |
| Method not allowed (e.g., `GET /v1/chat/completions`) | `405 { "error": "Method not allowed", "allowed": ["POST"] }` | info |
| Client disconnects mid-request | Abort upstream fetch, log as `client_disconnect`, no error response needed | info |
| Client sends request while daemon is shutting down | `503 { "error": "Daemon is shutting down" }` | info |
| Internal server error (bug in routing logic) | `500 { "error": "Internal router error", "request_id": "uuid" }` — include request_id for log correlation | error |

**Every error response** follows the same JSON shape:
```json
{
  "error": { 
    "message": "Human-readable description",
    "type": "error_type",
    "code": "machine_readable_code",
    "request_id": "uuid-for-log-correlation"
  }
}
```
This matches the OpenAI error format so coding tools can parse it natively.

### 10.3 Upstream Proxy Errors

Errors that occur when forwarding requests to providers.

| Scenario | Behavior | Circuit breaker impact |
|----------|----------|----------------------|
| DNS resolution failure | Retry on next model. Log: `"DNS resolution failed for api.groq.com"` | Counts as failure |
| TCP connection refused | Retry on next model immediately (no timeout wait) | Counts as failure |
| TLS handshake failure | Retry on next model. Log full TLS error for debugging | Counts as failure |
| HTTP 429 (rate limited) | Retry on next model. Extract `Retry-After` header if present, log it | Counts as failure + flag as `quota_exhausted` if remaining=0 |
| HTTP 500/502/503 | Retry on next model | Counts as failure |
| HTTP 401/403 (auth error) | Do **not** retry (all models at same provider will fail too). Mark as `AUTH_ERROR` | Does NOT count as failure |
| Response timeout (15s) | Abort fetch, retry on next model | Counts as failure |
| Malformed response (invalid JSON, missing fields) | Log the raw response (truncated to 1 KB), retry on next model | Counts as failure |
| Stream: connection drops mid-stream | If no data sent to client yet → retry. If partial data sent → let through, log error | Counts as failure |
| Stream: provider sends malformed SSE chunk | Skip the bad chunk, continue streaming. Log at warn level | Does NOT count as failure (transient) |
| Upstream returns HTML instead of JSON (maintenance page) | Detect via `Content-Type` header. Treat as 503, retry on next model | Counts as failure |

**Request ID propagation**: Every incoming request gets a UUID (`X-Request-Id`). This ID appears in:
- All log lines related to that request
- The error response if routing fails
- The SSE `request` event sent to the dashboard

This makes it trivial to trace a request through daemon logs: `grep "req-abc123" ~/.free-coding-models-daemon.log`

### 10.4 File I/O Errors

The daemon reads/writes several files. None of them should crash the process.

| File | Read failure | Write failure |
|------|-------------|---------------|
| Config (`~/.free-coding-models.json`) | Use last known good in-memory state. Log warning. Retry in 60s | Log warning. Retry in 60s. Daemon continues with in-memory state |
| Token stats (`~/.free-coding-models-tokens.json`) | Start with empty counters. Log warning | Buffer in memory. Retry on next flush (60s). If 5 consecutive failures → disable file writes, keep in-memory only, log error |
| PID file (`~/.free-coding-models-daemon.pid`) | N/A (write-only at startup) | Log error. Daemon still runs but TUI won't find it via PID. Port discovery will work as fallback |
| Port file (`~/.free-coding-models-daemon.port`) | TUI falls back to port scan | Same as PID file — daemon runs, discovery falls back to scan |
| Log file (`~/.free-coding-models-daemon.log`) | N/A (write-only) | Fall back to stderr (if available) or silently drop logs. Never crash over a log write failure |
| Config file corrupted (invalid JSON) | Treat as read failure — keep last known good state. Log: `"Config file corrupted, using cached state"` | N/A — we write valid JSON with atomic rename (`write tmp + rename`) |

**Atomic writes**: All file writes use the `write-to-temp-then-rename` pattern to prevent corruption from mid-write crashes:
```
write → /tmp/.free-coding-models-tokens.json.tmp
rename → ~/.free-coding-models-tokens.json
```

### 10.5 Memory Safeguards

The daemon runs indefinitely. Unbounded data structures = eventual OOM.

| Data structure | Hard cap | Eviction strategy |
|----------------|----------|-------------------|
| Health probe rolling window | 20 entries per model | Oldest dropped on insert (ring buffer) |
| Live request log (dashboard) | 200 entries | Oldest dropped on insert (ring buffer) |
| SSE client connections | 10 concurrent TUI connections max | Reject with `503` if exceeded (extremely unlikely) |
| Token stats in-memory buffer | Flush every 60s, then clear buffer | If flush fails, buffer grows — but capped at 10,000 entries, then oldest dropped |
| Daemon log buffer (in-memory before write) | 1,000 lines | Flush immediately on overflow |
| Circuit breaker state | 1 entry per model in all sets | Bounded by total models in sets (typically <50) |
| Pending upstream requests | 50 concurrent max | Return `503 { "error": "Router overloaded, too many concurrent requests" }` for new requests beyond limit |

### 10.6 Graceful Degradation Hierarchy

When things go wrong, the daemon degrades in layers — never jumps straight to "dead":

```
Level 0: FULLY OPERATIONAL
  All models healthy, probes running, stats tracking
           │
           ▼ (some models fail)
Level 1: DEGRADED ROUTING
  Some models OPEN/STALE, routing to remaining healthy ones
  Dashboard shows ● / ○ / 💀 mix
           │
           ▼ (all models in set fail)
Level 2: SET EXHAUSTED
  Returns 503 with detailed error + quota_exhausted info
  Probes continue — will auto-recover when models come back
           │
           ▼ (config file unreadable)
Level 3: CONFIG ISOLATION
  Running on cached in-memory state, no config writes
  Log warning every 60s. Routing still works with cached keys
           │
           ▼ (token file unwritable)
Level 4: STATS-ONLY DEGRADATION
  Routing works, but token stats are in-memory only (not persisted)
  Dashboard still shows live data, historical data may be stale
           │
           ▼ (10+ uncaught exceptions in 5min)
Level 5: SELF-RESTART
  Graceful shutdown + auto-respawn
  Brief downtime (~2-3s), tools get connection refused then reconnect
```

**The daemon never reaches "Level 6: dead" on its own.** Only `--daemon-stop`, `SIGKILL`, or system shutdown can kill it.

### 10.7 Error Telemetry

| Event | When | Properties |
|-------|------|------------|
| `app_router_error` | Any error at warn/error level | `{ error_type, code, model, request_id, degradation_level }` |
| `app_router_self_restart` | Level 5 self-restart triggered | `{ uncaught_count, uptime_before_restart }` |

Respects `telemetry.enabled` — no events if user opted out.

---

## 11. Daemon Auto-Start on System Boot

The daemon can optionally be configured to start automatically when the system boots, so the router is always available — even before the user opens the TUI.

### Configuration

A toggle in the **Settings screen** (P key) under a new "Router" section:

```
Router
  ├ Daemon auto-start on boot:  [ON] / OFF
  ├ Probe intensity:            Eco / [Balanced] / Aggressive
  └ Active set:                 fast-coding ▸
```

### Implementation

| Platform | Mechanism | File location |
|----------|-----------|---------------|
| macOS | `launchd` plist | `~/Library/LaunchAgents/com.free-coding-models.daemon.plist` |
| Linux | `systemd` user unit | `~/.config/systemd/user/free-coding-models-daemon.service` |

When the user toggles auto-start ON:
1. Generate the platform-appropriate service file
2. Register it (`launchctl load` / `systemctl --user enable`)
3. Show confirmation in TUI: `"✓ Daemon will start automatically on boot"`

When toggled OFF:
1. Unregister (`launchctl unload` / `systemctl --user disable`)
2. Remove the service file
3. Daemon keeps running for the current session (not killed)

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| User uninstalls `free-coding-models` globally | Service file becomes orphaned — harmless (launchd/systemd logs an error, no side effects). README documents cleanup command |
| Binary path changes after npm update | Service file references `npx free-coding-models --daemon` which resolves dynamically |
| Multiple user accounts on same machine | Each user gets their own service file + PID file + port |

---

## 12. Telemetry

The router integrates with the existing PostHog telemetry system (anonymous, opt-out respected).

### New Events

| Event name | When fired | Properties |
|------------|-----------|------------|
| `app_daemon_start` | Daemon process spawns | `{ port, set_count, models_in_active_set, auto_start, probe_mode }` |
| `app_daemon_stop` | Daemon graceful shutdown | `{ uptime_seconds, total_requests_routed, total_tokens }` |
| `app_router_failover` | Request-level failover occurs | `{ from_model, to_model, reason, attempt_number }` |
| `app_router_circuit_open` | Circuit breaker opens | `{ model, consecutive_failures, cooldown_ms }` |
| `app_router_set_switch` | User switches active set | `{ old_set, new_set, models_count }` |
| `app_router_set_create` | User creates a new set | `{ set_name, models_count }` |
| `app_router_install` | User installs FCM Router endpoint in a tool | `{ tool, set_name, endpoint_type }` |
| `app_router_all_down` | All models in set unavailable | `{ set_name, models_tried, quota_exhausted_count }` |
| `app_router_autostart_toggle` | User toggles daemon auto-start | `{ enabled, platform }` |

### Privacy

- No request/response content is ever sent
- No API keys or model outputs
- Only aggregate counts (tokens, requests) and structural events (failover, circuit state)
- Respects existing `telemetry.enabled` config flag — if user opted out, zero events fire

---

## 13. Development Phases From Here

The original PRD mixed backend, TUI, onboarding, and release work into broad phases. The plan below reflects what is already implemented and what should be tackled next without stepping on itself.

### Phase 1 — Backend Foundation ✅ Done

Shipped in the first implementation pass.

- ✅ Daemon process lifecycle: foreground, background, status, stop.
- ✅ PID file, port file, port fallback scan, and status discovery.
- ✅ Router logging with rotation.
- ✅ Router config schema under `router`.
- ✅ Config normalization that preserves router sets across unrelated saves.
- ✅ API key lookup: config first, env fallback.
- ✅ Config reload every 60s.
- ✅ OpenAI-compatible `/v1/chat/completions` reverse proxy.
- ✅ `/v1/models` virtual model list.
- ✅ Default `fast-coding` set creation.
- ✅ Graceful shutdown with in-flight drain and token flush.
- ✅ Basic daemon telemetry.
- ✅ README/config/flags/changelog documentation.

### Phase 2 — Backend Hardening & Compliance ✅ Done

Goal: make the router backend robust enough that the TUI can trust it without defensive hacks.

- ✅ Added mock-upstream integration tests for:
  - success routing
  - non-streaming failover
  - streaming failover before first byte
  - partial streaming failure behavior
  - auth errors
  - all-models-down `503`
  - malformed JSON / HTML upstream response
  - timeout and connection refused
  - client disconnect aborts
- ✅ Implemented client-disconnect upstream abort without counting it as provider failure.
- ✅ Detects upstream HTML maintenance pages and retries them as provider `503` failures.
- ✅ Treats malformed successful JSON as a retryable upstream failure.
- ✅ Extracts `Retry-After` and common rate-limit/quota headers when providers expose them.
- ✅ Adds `quota_exhausted_details` beside `quota_exhausted` in router `503` payloads.
- ✅ Removed `/daemon/restart` from the active API until a real service-level restart strategy exists.
- ✅ Auth failures now skip remaining same-provider candidates during the current request.
- ✅ Finished error telemetry:
  - `app_router_error`
  - `app_router_self_restart`
- ✅ Process safety decision: the daemon still recovers ordinary uncaught exceptions/rejections in-process, but exits after 10 uncaught exceptions in 5 minutes so launchd/systemd or the future TUI service manager can restart it. It does not self-spawn a second process from inside the daemon.
- ✅ Added package sanity coverage that `src/router-daemon.js` remains included by the npm `files` allowlist.

**Exit criteria**

- Router backend has deterministic integration tests with local fake providers.
- No advertised backend endpoint is stubbed or misleading.
- Backend behavior matches sections 8-10 of this PRD, or this PRD is updated with explicit deviations.

### Phase 3 — Router Dashboard TUI ✅ Done

Goal: make router health visible inside the existing terminal app.

- ✅ Added `Shift+R` global keybinding from the main TUI.
- ✅ Added Router Dashboard overlay plus Ctrl+P page entry.
- ✅ Connected dashboard to:
  - `GET /health`
  - `GET /stats`
  - `GET /stream/events`
- ✅ Rendered:
  - daemon state
  - active set
  - port
  - uptime
  - request count
  - probe mode
  - model health/circuit table
  - token summary
  - live request log
- ✅ Added local dashboard keys:
  - `S` switches to the next active set using `/sets` + `/sets/:name/activate`
  - `I` cycles probe intensity using `POST /daemon/probe-mode`
  - `R` shows a Phase 7 restart notice, because no real service manager restart path exists yet
  - `C` clears the local dashboard request log
  - `P` shows a disabled notice until backend probe pause/resume support exists
  - `Esc` returns to the main table
- ✅ Added defensive dashboard parsing for stopped, stale, unreachable, partial, and malformed daemon payloads.
- ✅ Added unit/integration tests for dashboard helpers, command palette entry, and probe-mode endpoint.
- ✅ Used `agent-tui` visual tests for dashboard layout and key handling.

**Exit criteria**

- ✅ User can inspect daemon/router state without leaving the TUI.
- ✅ Dashboard works when daemon is running, stopped, stale, or unreachable.
- ✅ TUI never crashes if the daemon returns malformed/unexpected JSON.

### Phase 4 — Set Manager & Model Set UX ✅ Done

Goal: make model sets manageable by normal users, not just HTTP clients.

- ✅ Added `Shift+S` global keybinding from the main TUI.
- ✅ Added two-pane TUI: left = set list (★ = active), right = ordered models in selected set.
- ✅ Added set actions via inline edit modes:
  - `N` → create new set (text input + Enter confirm, Esc cancel)
  - `D` → duplicate selected set (pre-fills name with "-copy" suffix)
  - `R` → rename selected set (text input + Enter confirm, Esc cancel)
  - `⌫` → delete with confirmation (Enter to confirm, Esc to cancel)
  - `A` → activate selected set with confirmation (Enter to confirm, Esc to cancel)
- ✅ Added model actions:
  - `⌫` while in models pane → removes selected model from set
  - `Shift+↑` / `Shift+↓` → reorder model priority within set
- ✅ Added `Shift+A` global add-selected-model flow (fetches sets, opens position picker).
- ✅ Added `Tab` key to switch focus between sets pane and models pane.
- ✅ Added `↑↓` navigation within active pane, PageUp/PageDn/Home/End.
- ✅ Persist via existing daemon `/sets`, `/sets/:name` (PUT/DELETE), and `/sets/:name/activate` endpoints.
- ✅ Added `setsManager` API helpers: `fetchRouterSets`, `createRouterSet`, `renameRouterSet`, `duplicateRouterSet`, `deleteRouterSet`, `activateRouterSet`, `updateRouterSetModels`, `removeModelFromRouterSet`, `reorderRouterSetModel`.
- ✅ Added `setsManagerOverlay` render: `renderSetsManager()` in overlays.js with cursor tracking and scroll management.
- ✅ Added `Shift+A` global add-model flow (position picker for insertion priority).

**Exit criteria**

- ✅ User can create and maintain router sets entirely inside the TUI.
- ✅ Priority order is visually clear and matches backend routing order.
- ✅ Deleting active set falls back safely and visibly (auto-activates first remaining set).
- ✅ All overlay states degrade cleanly when daemon is unreachable.

### Phase 5 — Token Usage UI & Main Status Indicator ✅ Done

Goal: expose token tracking and router state where users naturally look.

- ✅ Added main footer/status line showing:
  - `● Router: <set> Today: Ntok All-time: Ntok` when daemon is running
  - `○ Router: daemon not running  •  Shift+R Dashboard  •  Shift+S Sets` when daemon is down
- ✅ Token formatting matches spec: `< 1,000` raw, `K` with 2 decimals, `M` with 2 decimals
- ✅ Added `Shift+T` Token Usage screen fetched from `GET /stats/tokens` on the daemon
- ✅ Rendered:
  - today total/prompt/completion/request counts + all-time totals side by side
  - top models today with proportional bar chart (top 8)
  - last 7 days history chart (multi-row bar chart using block characters)
- ✅ Token stats polled every 30s in background so footer is always live without opening the dashboard
- ✅ Command palette includes Token Usage entry (`Shift+T`, icon 📊)

**Exit criteria**

- ✅ Users can answer "is the router running?" and "what did I use today?" from the TUI.
- ✅ Token views degrade cleanly when the token file is missing or daemon is unreachable (shows error state, not crash).

### Phase 6 — Onboarding & Install Flow ✅ Done

Goal: make the router discoverable and easy to install into coding tools.

- ✅ Add new-user onboarding overlay when `config.router` is absent.
- ✅ Add existing-user upgrade banner for users with existing config but no router key.
- ✅ Add "enable router" flow:
  - create default set from top healthy visible models when possible
  - start daemon
  - show dashboard or success confirmation
- ✅ Add "not now" flow:
  - `router.enabled = false`
  - `router.onboardingSeen = true`
- ✅ Add "FCM Router" as install target in endpoint installer.
- ✅ Write tool configs with:
  - `base_url: http://localhost:<port>/v1`
  - `model: fcm`
  - `api_key: fcm-local`
- ✅ Support named set install:
  - `base_url: http://localhost:<port>/v1/sets/:name`
  - `model: fcm`
- ✅ Add install telemetry (`app_router_install`) and usage telemetry (`app_router_use` — every 10 requests).
- ✅ Add command palette actions for router dashboard, sets manager, and token usage.

**Exit criteria** ✅ Met

### Phase 7 — Auto-Start & Service Management

Goal: make the router always available after reboot for users who opt in.

- Add Settings router section:
  - auto-start toggle
  - probe intensity
  - active set selector
- Implement macOS `launchd` plist:
  - `~/Library/LaunchAgents/com.free-coding-models.daemon.plist`
- Implement Linux systemd user unit:
  - `~/.config/systemd/user/free-coding-models-daemon.service`
- Use dynamic command that survives npm upgrades where possible.
- Add unregister/remove flow.
- Add auto-start telemetry:
  - `app_router_autostart_toggle`
- Document cleanup commands for orphaned services.

**Exit criteria**

- Opt-in auto-start works on macOS and Linux.
- Turning it off removes service files and does not kill the current session unexpectedly.

### Phase 8 — Release Hardening & npm Verification

Goal: ship the router without the local-repo blind spots that npm packages love to hide.

- Run full test suite:
  - `pnpm test`
  - `pnpm start`
  - daemon lifecycle smoke
  - mock upstream integration tests
  - `agent-tui` visual tests for router screens
- Run package/build verification:
  - `pnpm build:web`
  - `npm pack --dry-run`
  - verify `src/router-daemon.js` is included in the tarball
- Bump version.
- Rewrite `CHANGELOG.md` with only the release notes for the new version.
- Commit and push.
- Wait for GitHub Actions npm publish.
- Install the published package globally.
- Verify:
  - `free-coding-models --help`
  - `free-coding-models --daemon-bg`
  - `free-coding-models --daemon-status`
  - `free-coding-models --daemon-stop`

**Exit criteria**

- The published npm tarball, not only the local checkout, runs the router successfully.

---

## 14. Non-Goals (Explicitly Out of Scope)

| Out of scope | Why |
|-------------|-----|
| Cost tracking / billing | All models are free — no cost to track |
| API format translation (Claude/Gemini native) | All our providers are already OpenAI-compatible |
| Multi-account per provider | Complexity not justified for free tiers |
| Remote/cloud daemon | This is a local-first tool |
| Authentication on daemon endpoints | Localhost only — no auth needed |
| Model capability matching (auto-pick by task type) | Future enhancement, not v1 |
| Persistent request/response logging | Privacy concern — only metadata (tokens, latency, status) is stored |
| Set export/import (sharing) | Deferred to future version — focus on core routing first |
| Quota-aware scoring | Not in scoring algorithm — but quota exhaustion IS surfaced in 503 error messages so users understand why routing failed |

---

## 15. Success Metrics

| Metric | Target |
|--------|--------|
| Daemon uptime | >99.5% (auto-restart on crash) |
| Failover latency overhead | <2s for transparent retry |
| Health probe false positive rate | <5% (model marked OPEN when actually healthy) |
| Time from "model goes down" to "traffic rerouted" | <90s (3 failures × 30s probe interval in Balanced mode) |
| Time from "model goes down" to "traffic rerouted" (Aggressive) | <30s |
| User setup time | <30s from first seeing onboarding to having a working router |
| Eco probe token cost | ~0 tokens/day (uses models endpoint, not chat completions) |

---

## 16. Decisions Log

Decisions made during design, for reference:

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Daemon is a separate background process, UI integrated in TUI | Daemon survives TUI closure; UX feels unified |
| 2 | OpenAI-compatible only (no format translation) | All 25 providers already speak OpenAI format |
| 3 | Named sets with quick switching | Users have different needs (fast-coding vs deep-reasoning) |
| 4 | Token tracking only, no cost | Everything is free — cost is always $0 |
| 5 | Fixed port (19280) with fallback + discovery | Simple default, robust fallback |
| 6 | 503 on all-down with quota exhaustion detail | User gets actionable info, not just "unavailable" |
| 7 | Multi-endpoint routing (`/v1/sets/:name/...`) | Different tools can use different sets simultaneously |
| 8 | `usage.total_tokens` from response | Reliable, zero overhead, standard OpenAI field |
| 9 | 3 probe intensity modes (Eco/Balanced/Aggressive) | Eco uses zero-token HEAD checks; protects low-cap providers |
| 10 | Auto-start on boot via launchd/systemd | Router always available, toggle in Settings |
| 11 | PostHog telemetry for daemon lifecycle | Tracks adoption, failover frequency, set usage patterns |
| 12 | No set export/import in v1 | Deferred — core routing first |
| 13 | No quota-aware scoring | Quota surfaced in error messages instead — simpler, equally useful |
| 14 | API keys from config file (primary) + env vars (fallback) | Config file is the only source that works with auto-start on boot |
| 15 | Reverse proxy rewrites 3 fields only (URL, auth header, model) | Everything else passthrough — minimal mutation, maximum compatibility |
| 16 | No load balancing across models for concurrent requests | All go to best model — free tiers handle it fine, and if rate-limited the circuit breaker kicks in |
| 17 | Cold start = burst probe + fallback to user priority | Daemon usable in seconds, fully scored in ~10s |
| 18 | Stale model detection via sources.js cross-reference | Models removed by providers are skipped but kept in set |
| 19 | Daemon and TUI are always same version (same package) | No version mismatch handling needed — TUI spawns daemon from its own binary |
| 20 | Zero-crash architecture with 6-level graceful degradation | Daemon never exits on its own — degrades in layers from fully operational to self-restart |
| 21 | OpenAI-compatible error response format | Tools can parse errors natively, no custom error handling needed |
| 22 | Atomic file writes (tmp + rename) | Prevents corruption from mid-write crashes or power loss |
| 23 | All data structures have hard memory caps | Ring buffers and limits prevent OOM on long-running daemon |
