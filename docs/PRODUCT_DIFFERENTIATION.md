# Product Differentiation — Beyond a Merge

Merging FCC + FCM gives us "a proxy with a speed-test." That's table stakes.
This doc is about what makes the combined project **a different product** than
either base — grounded in the real pain of the person who uses these tools.

## 1. Who the user actually is, and what hurts

**The user:** a developer who won't pay for AI coding, so they run Claude Code /
Codex / OpenCode / Cline against *free or free-limited* providers (NVIDIA NIM,
Groq, Gemini free tier, OpenRouter free models, trial credits, local models).

**What their day actually feels like — the pains neither tool solves:**

| # | Pain | FCC today | FCM today |
|---|------|-----------|-----------|
| P1 | Free quota runs out mid-task with no warning (RPM / req-day / token-day / trial credits) | no awareness | no awareness |
| P2 | Failover is **reactive** — you eat a failed request *then* it switches | within-stream retry only | fails over only after a failure |
| P3 | "Best" model is ranked by **latency**, not whether its code is actually good | n/a | stability = speed/uptime, not quality |
| P4 | Multiple keys for one provider aren't pooled — free capacity left on the table | no | no |
| P5 | Requests routed to models that can't do the job (no tool-use / too-small context / no vision) → silent garbage | capability data exists but not used at routing time | latency-only routing |
| P6 | Sending proprietary code to providers that **train on your prompts** (e.g. free tiers) with no guardrail | egress scheme guard only | none |
| P7 | 190k conversation routed to a 32k model → hard failure | no context guard | no context guard |
| P8 | When something breaks, no way to see *why* (model? truncation? tool-parse? rate limit?) or replay it | traces exist, not user-facing | none |
| P9 | Silent quality cliff — you don't know your agent just dropped to a weak model | no signal | no signal |
| P10 | Key/config sprawl across 26 providers and many tool config files | managed `~/.freeway` | `~/.free-coding-models.json` |

**Punchline:** "free" is only useful if it's *reliable, trustworthy, and
stretches as far as possible*. Both tools stop at "route to something that's
up." The differentiation is everything after that.

## 2. Positioning (north star)

> FCC is a dumb pipe. FCM is a speed-test. **Ours is an intelligent free-AI
> gateway that stretches your free quota the furthest, routes by what the task
> needs and what your data policy allows, and shows you exactly what happened.**

Four pillars: **Fuel · Brains · Trust · Glass box.**

## 3. The differentiating features

### Pillar 1 — FUEL: make "free" go furthest  *(solves P1, P4)*
- **Quota Governor** — model each provider/key's real free limits (RPM,
  req/day, tokens/day, trial-credit balance). Track live consumption and route
  **proactively away from near-exhausted providers before the 429**, not after.
  Show a "free fuel gauge" and predict time-to-exhaustion. *This is the flagship
  — nobody does proactive quota budgeting.*
- **Multi-key pool & rotation** — pool N keys per provider to multiply free
  capacity; auto-park a rate-limited key and revive it when its window resets
  (daily/per-minute), tracked per provider.
- **Response cache (exact + semantic)** — coding agents repeat a lot (re-reads,
  near-identical prompts). Cache idempotent responses locally to spend *zero*
  quota on repeats.
- **Cache-affinity routing** — keep a conversation on the same provider to hit
  its prompt cache (DeepSeek/Anthropic-style), saving quota and latency.

### Pillar 2 — BRAINS: route by what the task needs  *(solves P3, P5, P7)*
- **Capability-aware routing** — FCC already knows provider capabilities; use
  them at routing time. Task needs tool-use / vision / 128k context / thinking?
  Only route to models that actually support it. Kills silent failures.
- **Context-window guard + adaptive compaction** — never route a conversation
  larger than the target model's window; compact/summarize to fit *per target*.
- **Task-tiered quality routing** — classify the request (trivial edit vs hard
  refactor) and route trivial → fastest free model, hard → best free S-tier.
- **Quality floor** — user sets a minimum tier; the router refuses to silently
  drop below it (asks or waits instead).
- **Inline model directives (@-mentions)** — type a sigil-tagged token in the
  prompt to override routing for **that request**: `@fast`/`@best`/`@cheap`/
  `@local` (semantic aliases), `@groq` (provider), `@glm-4.6` (specific model),
  `@set:coding` (named set), user-defined aliases (`@review` → your bound
  model), and a sticky form (`@groq!`) to pin for the session. The router scans
  the latest user turn, overrides the resolved model, and strips the token
  before forwarding upstream. Manual control that rides on top of auto-routing;
  also serves as the keyword→model binding mechanism.
  - *Constraint:* one API call = one model, so a directive sets the model for
    the whole message, not literally per-word. (Per-word/sub-task splitting
    would need a planner — stretch goal.)
  - *Collision safety:* parse only a standalone token in the latest user
    message (never inside code fences); optional namespaced form `@fcc:groq` or
    rarer sigil `>>groq`; escape with `\@`; global toggle to disable.
  - *Fallback:* if the tagged model is down / out of quota / incapable of the
    task, fall back per policy and signal the downgrade (never silent).
  - *One directive per prompt:* only **distinct targets** conflict (repeats /
    same-target tokens don't). On conflict, use the **first occurrence** and
    record the ignored tags in the response/Inspector (never swallow it).
    First-vs-last is a toggle; default first.
  - *Config UI — the alias table (the real feature):* a managed, cross-surface
    (TUI/web/desktop) table of `keyword → target`, target chosen from the
    **live model list** (`/v1/models` + catalog) — a specific model, provider,
    set, or semantic class (`fast`/`best`). Built-ins (`@fast`/`@best`/…) ship
    as editable default rows.
    - **Sigil stays required even for custom words** — the UI configures the
      word, but it only triggers as `@word`, never as a bare word in prose (so
      binding common tokens like `test`/`sql` can't hijack every prompt). Opt-in
      per-row "match bare word too" toggle, off by default, with a warning.
    - **Live status in the picker** (up/down + quota from the Governor/benchmark
      data) so users bind to working models; if a bound model later dies, the
      mapping still resolves but the router falls back + signals.
    - **Lint/validation:** block duplicate keywords; warn on collision-prone
      choices (words that are also real provider/model names or very common
      tokens).
    - **Scope:** global by default, optional **per-workspace/repo** overrides
      (ties into per-workspace policy). **Import/export** as small JSON to share.
  - *Deterministic resolution order:* (1) scan latest user turn for standalone
    `@`-tokens outside code fences → (2) map via alias table → (3) if >1 distinct
    target, take first + record ignored → (4) capability/quota check → fallback
    + signal if unusable → (5) strip token before forwarding upstream.

### Pillar 3 — TRUST: respect the user's code  *(solves P6)*
- **Data-governance routing** — tag every provider with its data policy (trains
  on prompts? retains? region?). User sets policy: *"never send my code to
  training-on providers"*, *"EU-region only"*, *"local-only for this repo."*
  Router honors it. Huge for professionals nervous about free tiers.
- **Per-workspace policy** — a sensitive repo pins to local/private providers
  automatically.
- **Egress secret-scrub** — extend FCC's egress guard to redact detected
  secrets/keys before they leave the machine.

### Pillar 4 — GLASS BOX: transparency + a feedback loop  *(solves P8, P9, P3)*
- **Request Inspector** — turn FCC's structured traces into a local UI: every
  request's prompt, the model it was routed to **and why**, tokens, cache hits,
  tool calls, and failure cause.
- **Replay & A/B compare** — re-run any request against a different model to
  compare output side-by-side. Makes the black box glass.
- **Honest downgrade signaling** — on failover, surface "downgraded GLM-4.6 (S)
  → Llama-3.1-8B (B), reason: rate limit" instead of degrading silently.
- **Personalized quality score** — learn from the user's *accepted vs rejected*
  agent edits per repo/language. Over time, "which free model actually works
  **for me**" replaces generic SWE-bench tiers. This is a feedback moat.

### Stretch / moat ideas
- **Community health feed (opt-in)** — anonymized, aggregated provider health so
  a new user instantly sees what's up *right now* without probing. Network
  effect; privacy-sensitive, infra-heavy — later.
- **Free-tier Autopilot** — extends FCM's auto-heal into a fully hands-off mode:
  continuously assembles the best working set from whatever keys you have,
  driven by quota + quality + capability. The "it just works" layer.

## 4. How this layers onto the merge plan

The merge plan's Phase 2 (health store) and Phase 3 (router) are the insertion
points — differentiators extend them rather than being bolted on later:

| Differentiator | Hooks into merge phase | Effort | Priority |
|---|---|---|---|
| Quota Governor | extend P2 health store + P3 router | M | **1 (flagship)** |
| Multi-key pool & rotation | P3 router | M | **2** |
| Capability + context-aware routing | P3 router (uses FCC capability data) | M | **3** |
| Inline model directives (@-mentions) | P3 router pre-step | S | **3.5 (quick win)** |
| Request Inspector + honest downgrade | P4 UI (uses FCC traces) | S–M | **4** |
| Data-governance routing | P3 router + provider catalog tags | M | **5** |
| Response cache + cache-affinity | P1/P3 | M | 6 |
| Task-tiered quality routing | P3 + classifier | M | 7 |
| Personalized quality score | P4 + feedback loop | L | 8 |

S ≈ ≤1 wk · M ≈ 1–2 wk · L ≈ 2–4 wk.

## 5. The recommended build order (the plan)

Do the merge Phases 0–1 first (one endpoint for all tools). Then interleave the
differentiators with the router work, cheapest-highest-value first:

1. **D1 — Quota Governor** (with P2). The headline. Proactive quota routing +
   fuel gauge. This alone justifies the new project.
2. **D2 — Multi-key pooling** (with P3). Multiplies free capacity — pure user win.
3. **D3 — Capability + context-aware routing** (with P3). Kills silent failures;
   nearly free since FCC already has the capability metadata.
4. **D4 — Request Inspector + honest downgrade** (with P4). Cheap given FCC's
   existing traces; massive trust/UX payoff.
5. **D5 — Data-governance routing** (with P3/catalog). The pro-user unlock.
6. **D6 — Response cache, task-tiered routing, personalized quality** — deepen
   the moat once the core is proven.

**Why this order:** D1–D3 make free *actually reliable* (the core promise),
D4 makes it *trustworthy to debug*, D5 makes it *safe for real work*, D6 makes
it *smarter than anything else over time*. Each ships as a locally testable
increment (Node `pnpm test` / Python `uv run pytest`), no remote needed.

## 6. One-line differentiation vs the bases

- **vs free-claude-code:** it stops at "translate + route to one provider." We
  add fuel/brains/trust/glass-box so free is reliable, not just reachable.
- **vs free-coding-models:** it stops at "which model is fastest right now." We
  route by quota + capability + data policy + *your* quality history, and serve
  Claude Code & Codex natively (which FCM can't).
