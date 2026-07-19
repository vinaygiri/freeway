# Security Policy

Freeway is a **local, loopback-first** gateway: the proxy and its admin control
center bind to `localhost` and are meant to run on your own machine. It stores
provider API keys in your local config (`~/.freeway/.env`) and never transmits
them anywhere except to the upstream provider you configured. Even so, because
Freeway handles credentials and proxies model traffic, we take security reports
seriously.

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.5.x   | ✅ |
| < 2.5   | ❌ (please upgrade) |

Security fixes land on the latest `2.5.x` line. The current version is in
`proxy/pyproject.toml`.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Report privately via **GitHub Private Vulnerability Reporting**: on this
repository, go to the **Security** tab → **Report a vulnerability**. This opens a
private advisory that only you and the maintainers can see.

> Maintainers: enable this under **Settings → Code security → Private
> vulnerability reporting**.

Please include:
- A description of the issue and its impact.
- Steps to reproduce (a minimal proof of concept if possible).
- Affected version and platform.

We aim to acknowledge a report within **72 hours** and to provide a remediation
timeline after triage. Please give us a reasonable window to release a fix before
any public disclosure (coordinated disclosure).

## Scope

In scope:
- The proxy (`proxy/`) — request routing, protocol translation, credential
  handling, the loopback admin API/UI.
- The CLI launchers (`freeway`, `freeway-claude`, `freeway-codex`, `freeway-init`).
- The web dashboard (`frontend/`).

Out of scope:
- Vulnerabilities in upstream model providers or in third-party dependencies
  (report those to their maintainers; we will update pinned versions).
- Issues that require an attacker to already have local access to a machine where
  you have deliberately exposed the loopback service to the network.

## Handling your API keys safely

- Keys live only in `~/.freeway/.env` (created by `freeway-init`) — **never commit
  them.** The repo's `.gitignore` excludes `.env` files.
- The admin UI is **loopback-only**. Do not expose the proxy port to the public
  internet or bind it to `0.0.0.0` on an untrusted network without adding your own
  authentication and TLS in front of it.
- Set `ANTHROPIC_AUTH_TOKEN` so local clients must present a token to use the proxy.
- Freeway records request **metadata only** (model, tokens, outcome) in the
  inspector — never prompt content.

Thank you for helping keep Freeway and its users safe.
