# Freeway as a Python library — public API design (draft for review)

## Why this exists

Freeway today is an *application* (a proxy server). This document proposes exposing its
core — provider routing, cross-provider failover, multi-key rotation, and tool-schema
compression — as an **importable Python package**, with the existing proxy re-expressed as a
thin server *on top of* that library.

Two audiences, one core:

- **Library users** (`import freeway`) — Python developers who want resilient free-tier LLM
  routing *inside their own app/agent*, without running a separate proxy.
- **Proxy users** (`freeway serve`) — Claude Code / Codex users, exactly as today.

The proxy becoming a consumer of the library is itself the point: it proves the core is a
clean, reusable unit rather than tangled into the web layer.

## Goals / non-goals

**Goals**
- A small, obvious, OpenAI-shaped API that works in 10 lines.
- Failover, multi-key rotation, and tool compression are **built in and transparent** — the
  caller gets them for free and can *see* what happened (which model served, did it fail over).
- Sync **and** async, streaming **and** buffered.
- Zero behavioural divergence from the proxy — same routing decisions, same code path.

**Non-goals**
- Not a new feature surface. No new providers, no new compression engines. This is a
  *repackaging*, not a rewrite.
- Not breaking the proxy. `freeway serve` keeps working identically.

## Public surface

```python
from freeway import Freeway

fw = Freeway(
    primary="gemini/models/gemini-2.5-flash",
    fallbacks=["cerebras/gpt-oss-120b", "groq/llama-3.3-70b-versatile"],
    keys={                                   # multi-key rotation (round-robin) built in
        "gemini":   ["k1", "k2"],
        "cerebras": "csk-...",
        "groq":     "gsk-...",
    },
    auto_fit=True,        # True = adaptive (90% of model ctx); int = explicit budget; False = off
    compress_tools=True,  # v2.6.0 tool-schema compression when over budget
)
```

Convenience constructors:

```python
Freeway.from_env()                 # read keys + config from environment and ~/.freeway/.env
Freeway.from_config("~/.freeway/.env")
```

### Calling it

```python
# buffered (OpenAI-shaped messages in, normalized result out)
completion = fw.chat(
    messages=[{"role": "user", "content": "Refactor this function ..."}],
    tools=[...],            # OpenAI function-tool schema; compressed internally if over budget
    max_tokens=1024,
)
print(completion.text)

# streaming
for event in fw.stream(messages=[...]):
    if event.type == "text":
        print(event.text, end="")

# async variants
completion = await fw.achat(messages=[...])
async for event in fw.astream(messages=[...]):
    ...
```

### Return type — failover is *observable* (a differentiator vs a black-box gateway)

```python
@dataclass
class Completion:
    text: str
    tool_calls: list[ToolCall]         # normalized (name, arguments)
    stop_reason: str                   # end_turn | max_tokens | tool_use | ...
    served_model: str                  # the model that ACTUALLY answered
    was_fallback: bool                 # did the primary fail and we failed over?
    candidates_tried: int
    input_tokens: int
    output_tokens: int | None
    raw: dict                          # full underlying provider response, escape hatch
```

Streaming yields `StreamEvent`s (`type` ∈ `text | tool_call | done`); the terminal `done`
event carries the same metadata (`served_model`, `was_fallback`, tokens).

### Introspection (reuses existing machinery)

```python
fw.models()          # -> list[ModelInfo]  (discovered/available across configured providers)
fw.verify("cerebras/gpt-oss-120b")   # -> VerifyResult (live probe: live|rate_limited|down)
```

### Errors

```python
from freeway import AllProvidersFailed, ProviderAuthError
try:
    fw.chat(messages=[...])
except AllProvidersFailed as e:      # the whole chain was exhausted
    print(e.attempts)                # per-candidate reasons
```

## How it maps onto existing internals (no rewrite)

The facade is a thin wrapper over the code paths the proxy already uses:

| Public API | Reuses |
|---|---|
| `Freeway(...)` construction | build a `Settings` (`config/settings.py`) from args/env + a `provider_getter` (providers runtime) |
| `fw.chat()/.stream()` | construct `MessagesRequest` (`api/models/anthropic.py`) → `MessagesHandler.create()` (`api/handlers/messages.py`, already `async`, constructor-injected: `settings` + `provider_getter`) |
| routing | `ModelRouter` (`api/model_router.py`) — unchanged |
| failover | `ProviderExecutionService.stream_with_failover` (`api/provider_execution.py`) — unchanged |
| compression / auto-fit | `api/auto_fit.py` — unchanged |
| multi-key rotation | `providers` key pool — unchanged |
| OpenAI-shaped in/out | existing `core/openai_chat_completions` ↔ `core/anthropic` converters |
| `fw.verify()` | `core/model_probe` — unchanged |

The facade’s only real work: (1) accept OpenAI-shaped args and convert to the internal
`MessagesRequest`, (2) drive `MessagesHandler.create()` **without FastAPI**, (3) adapt the
returned SSE/stream into `Completion` / `StreamEvent`. `MessagesHandler` already takes plain
constructor args (not FastAPI `Depends`), so no HTTP is involved.

The proxy (`server.py` / handlers) is then refactored to call the **same facade**, so both
front-ends share one core.

## Package layout / naming

- Import name: `freeway` (top-level `freeway/__init__.py` exports `Freeway`, `Completion`,
  `StreamEvent`, exceptions).
- PyPI: `freeway-ai` (metadata already reserved in `pyproject.toml`).
- CLI unchanged: `freeway` / `freeway-serve` runs the proxy (now on top of the library).
- Existing `api/`, `core/`, `providers/`, `config/` stay put; `freeway/` is a facade module
  that imports them — minimal churn.

## Implementation phases

1. **Facade + result types** (`freeway/__init__.py`, `freeway/_facade.py`): `Freeway`,
   `chat`/`achat`/`stream`/`astream`, `Completion`/`StreamEvent`, exceptions. Thin — delegates
   to `MessagesHandler`.
2. **Refactor the proxy** to construct requests and call the facade (or the shared handler),
   proving the layering. Full suite must stay green.
3. **Docs + tests**: a `README` quickstart built around the 10-line example, an
   `examples/` dir (sync, async, streaming, failover-visible, tool-use), unit tests for the
   facade’s conversion + metadata surfacing.
4. **Publish** to PyPI (`freeway-ai`), add `pip install freeway-ai` to the README.

## Open questions (for your review)

1. **Primary input shape** — OpenAI-chat-shaped (proposed, most familiar to Python devs) vs
   also exposing Anthropic-shaped `messages`. Recommend: OpenAI-shaped public API, Anthropic
   available via `raw`/an escape hatch.
2. **Sync-over-async** — `chat()` wraps `achat()` via `asyncio.run`; fine for scripts, but
   document that inside an existing event loop you must use the async methods.
3. **Scope of v1** — ship `chat/stream/achat/astream` + `models/verify` first; leave
   messaging/admin/telegram/discord out of the library (proxy-only concerns).
4. **Naming** — `Freeway` as the entry class, or `Client` / `Router`? (`Freeway` is
   memorable and on-brand; `Client` is conventional.)
