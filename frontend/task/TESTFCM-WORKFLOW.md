# /testfcm Workflow

## Goal

Run a repeatable AI-assisted end-to-end check of `free-coding-models` that:

1. opens the real TUI in a PTY
2. selects a model through the normal launcher path
3. launches a real coding tool
4. sends `hi`
5. captures the answer or the failure
6. snapshots the useful logs and config artifacts
7. writes a Markdown report under `task/reports/`

## Preferred command

Use `pnpm test:fcm` when `pnpm` exists.

If `pnpm` is not installed, use:

```bash
npm run test:fcm --
```

Useful flags:

```bash
pnpm test:fcm -- --tool crush
pnpm test:fcm -- --tool codex
pnpm test:fcm -- --tool claude-code --tool-bin-dir test/fixtures/mock-bin
pnpm test:fcm -- --tool-bin-dir test/fixtures/mock-bin
pnpm test:fcm -- --prompt "hi"
pnpm test:fcm:mock:claude
```

## What the runner does

The runner lives at [scripts/testfcm-runner.mjs](../scripts/testfcm-runner.mjs).

It will:

1. copy `~/.free-coding-models.json` into an isolated HOME inside `task/artifacts/<run-id>/home`
2. normalize the copied config so only configured providers stay enabled and the proxy uses an OS-assigned port
3. force a predictable launch setup for the chosen tool
4. run a `--json` preflight to catch obvious startup regressions
5. start the real TUI in a PTY via the system `expect` command
6. wait for the screen to settle, then press `Enter`
7. wait for the launched tool, then send `hi`
8. classify the transcript as:
   - passed
   - failed
   - blocked
9. copy useful evidence into `task/artifacts/<run-id>/`
10. write `task/reports/testfcm-<run-id>.md`

The repo-local `test/fixtures/mock-bin/claude` fixture is special: it behaves like a tiny Claude CLI, but it still sends real Anthropic-style requests to the local FCM proxy. That makes it the preferred smoke test for Claude launcher regressions when the real `claude` binary is unavailable or too stateful for CI-like debugging.

## Evidence the AI must inspect

The runner already copies these when they exist:

- `task/artifacts/<run-id>/preflight-stdout.txt`
- `task/artifacts/<run-id>/preflight-stderr.txt`
- `task/artifacts/<run-id>/tool-transcript.raw.txt`
- `task/artifacts/<run-id>/tool-transcript.txt`
- `task/artifacts/<run-id>/request-log.jsonl`
- `task/artifacts/<run-id>/daemon.json`
- `task/artifacts/<run-id>/daemon-stdout.log`
- `task/artifacts/<run-id>/daemon-stderr.log`
- copied tool config files such as `crush.json` or `settings.json`

## What counts as success

Success is intentionally simple:

- the tool opens
- the AI sends `hi`
- the captured transcript contains an assistant-like reply such as `hello` or `how can i help`

## What counts as a useful failure

The workflow is still valuable when it fails.

Examples:

- invalid or missing API key
- tool binary missing from `PATH`
- proxy startup or routing problem
- tool launch crash
- no assistant reply within the timeout

Those failures should end up in the Markdown report with:

- exact evidence excerpt
- relevant artifact file paths
- concrete tasks to fix

## After the report exists

The AI should:

1. open the newest file in `task/reports/`
2. summarize the blockers in plain language
3. point to the exact evidence files
4. propose the next fix tasks
5. ask the user whether it should apply those fixes now
