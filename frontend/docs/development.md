# Development

## Setup

```bash
git clone https://github.com/vava-nessa/free-coding-models
cd free-coding-models
pnpm install
pnpm start
```

## Architecture

| File | Role |
|------|------|
| [`bin/free-coding-models.js`](../bin/free-coding-models.js) | Main CLI entrypoint — TUI, pinging, key handling |
| [`src/utils.js`](../src/utils.js) | Pure helpers: sorting, filtering, scoring, `parseArgs` |
| [`src/opencode.js`](../src/opencode.js) | OpenCode launch logic |
| [`src/opencode-config.js`](../src/opencode-config.js) | OpenCode config read/write |
| [`src/tool-launchers.js`](../src/tool-launchers.js) | All external tool launchers |
| [`src/endpoint-installer.js`](../src/endpoint-installer.js) | `Y` flow — install provider into tool config |
| [`sources.js`](../sources.js) | Model catalog — all 160 models across 20 providers |

## Tests

```bash
pnpm test        # unit tests (node:test, zero deps)
pnpm test:fcm    # AI E2E flow — drives the real TUI in a PTY
pnpm test:fcm:mock  # same but with a mock binary
```

Tests live in `test/test.js`. Pure logic lives in `src/utils.js` so it can be tested without mocking the TUI.

## Releasing

1. Update `changelog/vX.Y.Z.md` with the release notes for the new version
2. Bump `"version"` in `package.json`
3. Commit with just the version number as the message:

```bash
git add .
git commit -m "0.1.4"
git push
```

GitHub Actions auto-publishes to npm on every push to `main`. Verify with:

```bash
npm view free-coding-models version
npm install -g free-coding-models@<new-version>
free-coding-models --help
```
