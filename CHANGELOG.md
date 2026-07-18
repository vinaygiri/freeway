# Changelog

All notable changes to Freeway are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and Freeway follows
[Semantic Versioning](https://semver.org/) (the version lives in
`proxy/pyproject.toml`).

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
