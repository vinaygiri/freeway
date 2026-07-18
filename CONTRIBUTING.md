# Contributing to Freeway

Thanks for your interest in improving Freeway! This guide covers how to set up,
make changes, and open a pull request. By participating you agree to the
[Code of Conduct](./CODE_OF_CONDUCT.md).

Freeway is a workspace with **two independent subprojects**:

| Subproject | Stack | Detailed guide |
|---|---|---|
| `proxy/` | Python 3.14, `uv`, FastAPI (the data plane + `/admin` UI) | [`proxy/AGENTS.md`](proxy/AGENTS.md), [`proxy/ARCHITECTURE.md`](proxy/ARCHITECTURE.md) |
| `frontend/` | Node ≥18, `pnpm` (optional web dashboard / model catalog) | [`frontend/AGENTS.md`](frontend/AGENTS.md) |

Always `cd` into the relevant subproject before running its tooling.

## Getting started

**Proxy (Python):**
```bash
cd proxy
# install uv (https://astral.sh/uv) and Python 3.14 first
uv run uvicorn server:app --host 0.0.0.0 --port 8082   # run from source
uv run pytest -v --tb=short                            # tests
```

**Frontend (Node):**
```bash
cd frontend
corepack pnpm install
pnpm test          # unit tests
pnpm start         # run the TUI
pnpm build:web     # build the dashboard
```

## Before you open a PR

**Proxy** — run the full local CI (it must be green):
```bash
cd proxy
./scripts/ci.sh          # macOS / Linux
.\scripts\ci.ps1         # Windows
```
This runs, and CI enforces, five gates: a ban on `# type: ignore` / `# ty: ignore`
suppressions, `ruff format`, `ruff check`, `ty` (type check), and `pytest`.

- **Do not** add `# type: ignore` / `# ty: ignore` — fix the underlying type issue.
- Add tests for new behavior, including edge cases. Prefer real assertions over
  vacuous ones; don't `.skip` a test to make it pass.
- Keep provider modules independent — shared Anthropic/Responses logic goes in
  neutral `core/` modules, never imported from another provider's module.
- If your change touches a **production path** (`api/`, `cli/`, `config/`, `core/`,
  `messaging/`, `providers/`, `.env.example`, `pyproject.toml`, install/CI scripts),
  bump `[project].version` in `proxy/pyproject.toml` and run `uv lock` in the same
  change. See the versioning section in `proxy/AGENTS.md`.

**Frontend** — after any change to shared core (`src/`, `sources.js`), make sure it
works on **all three surfaces** (CLI/TUI, web dashboard, Tauri desktop). Run
`pnpm test` until green, then `pnpm start` to confirm no runtime errors.

## Pull request guidelines

- Keep PRs focused — one logical change per PR.
- Write a clear description: what changed, why, and how you verified it.
- Update docs (`README.md`, `CHANGELOG.md`, the in-app guide) when behavior changes.
- Reference any related issue.
- Be kind and constructive in review — see the Code of Conduct.

## Reporting bugs & requesting features

- **Bugs / features:** open a GitHub issue with clear reproduction steps or a
  concrete use case.
- **Security vulnerabilities:** do **not** open a public issue — follow
  [`SECURITY.md`](./SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](./LICENSE).
