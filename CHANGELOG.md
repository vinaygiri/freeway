# Changelog

All notable changes to Freeway are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and Freeway follows
[Semantic Versioning](https://semver.org/) (the version lives in
`proxy/pyproject.toml`).

## [2.5.4] — 2026-07-19 · reliability hardening ("never stops")

An adversarial audit of the whole request lifecycle (both protocols) found and
fixed several ways a run could silently stop or mask a truncation:

### Fixed
- **Failover was hard-capped at 3 attempts** regardless of how many fallback
  providers you configured. If your top 3 all hit a simultaneous free-tier
  rate-limit burst, the remaining fresh providers were never tried and the run
  stopped. It now walks the **whole configured chain**. (Live-verified: a
  5-provider chain with 4 failures serves from the 5th.)
- **Truncated tool call reported as a clean stop.** When output was cut off by
  the token limit *during a tool call*, the stop reason was overwritten to
  `tool_use`, hiding the truncation — the client would run a possibly-incomplete
  tool and move on. `max_tokens` is now preserved.
- **Non-standard `finish_reason` values masked truncation.** Providers that
  report truncation with a non-standard value (case variants like `LENGTH`, or
  aliases like `max_tokens`/`model_length`) were mapped to a clean `end_turn` →
  silent stop. `map_stop_reason` is now case-insensitive and alias-aware.
- **Abnormally-ended Chat Completions streams reported `finish_reason: stop`**
  (a clean finish) instead of `length` — the Chat analog of the 2.5.2 Responses
  `incomplete` fix.
- **Slow failover on rate limits.** A `429` triggered up to 5 same-provider retries
  (~30s of exponential backoff) *before* failover. Since a per-minute limit rarely
  clears in seconds, Freeway now fails over to a **fresh provider fast** (one quick
  retry, then move on); `5xx` keeps the full backoff.
- **Empty completion made the agent stop.** A provider returning a *completely
  empty* response (no text, reasoning, or tool call — a common free-tier glitch)
  produced a blank turn the agent treated as done. It now fails over to another
  provider instead.

## [2.5.3] — 2026-07-18

### Changed
- **Packaging: PyPI-ready.** Added package metadata (author, `MIT` license,
  keywords, classifiers, project URLs) so Freeway can be installed globally with
  `uv tool install freeway-ai` or `pipx install freeway-ai`.

### Added
- **Guidance to spread across providers.** The User Guide and the Limits page now
  explain per-provider free-tier caps (e.g. OpenRouter = 50 req/day, resets UTC
  midnight) and recommend picking favourites/fallbacks from 2–3 providers so one
  provider's cap can't stop you.

### Fixed
- Security/conduct reporting now routes through GitHub's private vulnerability
  reporting instead of an email placeholder.
- Synced `proxy/LICENSE` copyright holder to match the root license.

## [2.5.2] — 2026-07-18

### Fixed
- **Codex stopped mid-task with no error.** When a `/v1/responses` (Codex) reply
  was **truncated by the output-token limit** — a free-tier provider's per-response
  output cap, or the request's `max_output_tokens` — the proxy still reported
  `response.completed`, so Codex treated the turn as a clean finish and silently
  stopped (saying "continue" resumed exactly where it left off). The Responses
  assembler now reads the model's `stop_reason` and, on truncation, emits
  **`response.incomplete`** with `incomplete_details: {reason: "max_output_tokens"}`
  — the spec-correct signal — instead of a false `completed`. Normal completions
  are unchanged.

## [2.5.1] — 2026-07-18

### Fixed
- **Request Activity showed the current request at the bottom.** The list was
  reversed on render, so the most recent (currently running) request was buried
  at the end of a long history. Activity is now **newest-first**, with the active
  request at the top.
- **Dashboard "Active model" could show a stale model.** The "from last request"
  value was reading the *oldest* recorded request instead of the most recent; it
  now reflects the model that actually served your latest call.

### Added
- **Activity page now answers "which model is running?" at a glance.** A summary
  card at the top shows the most recent request's **served model**, whether it was
  the **primary or a fallback**, its **input-token count**, **status**, and **when**
  it ran.
- **Per-request Time and Input-tokens columns** in the Activity table, alongside
  the served model, a **primary/switched** fallback badge (hover for the demotion
  reason), and a **status** badge (hover for the error message on failures).

### Notes
- Per-request **output/total token** capture is not included yet (it requires
  tapping the stream's final usage). Input tokens — the figure that matters for
  free-tier per-minute limits — are shown today; full in/out/total is on the
  roadmap.

## [2.5.0] — 2026-07-16 · first public release

### Added
- **Mid-request cross-provider failover ("never stops").** Previously Freeway
  could only fail over *before* a response started. Now, if a provider accepts a
  request but fails **before producing any output** (rate-limit, overload, 5xx,
  bad model), Freeway re-routes to the next model in your chain and still
  completes the response — so a run no longer dies on one provider's hiccup.
  Verified live across providers (Cerebras ⇄ Gemini).
- **Adaptive auto-fit on by default** — over-budget requests are trimmed to the
  routed model's context (largest non-essential tool schemas first, then oldest
  whole turns), so a request can't be rejected for size. Only requests that would
  otherwise fail are touched.

### Changed
- **First public release under the Freeway brand.** Full documentation pass:
  accurate provider count (**26 providers** — 23 free-tier cloud + 3 local),
  rewritten proxy README, refreshed in-app User Guide and architecture docs, and
  regenerated screenshots. Attribution to the upstream MIT projects
  (`free-claude-code`, `free-coding-models`) preserved in `NOTICE` / `LICENSES/`.
