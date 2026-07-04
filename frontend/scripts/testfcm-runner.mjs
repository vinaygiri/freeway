#!/usr/bin/env node
/**
 * @file scripts/testfcm-runner.mjs
 * @description Expect-driven end-to-end runner behind the `/testfcm` workflow.
 *
 * @details
 *   📖 This runner uses the system `expect` binary to allocate a real PTY and
 *   📖 drive `free-coding-models` like a user would. That keeps the workflow
 *   📖 reliable even when JS PTY libraries are flaky on contributor machines.
 *
 *   📖 The flow is intentionally narrow and repeatable:
 *   📖 1. copy the user's FCM config into an isolated HOME
 *   📖 2. run a JSON preflight
 *   📖 3. start the real TUI through `expect`
 *   📖 4. wait a bit, press Enter, wait again, send `hi`
 *   📖 5. capture the entire transcript, logs, and tool config
 *   📖 6. classify the outcome and write a Markdown report in `task/reports/`
 *
 * @functions
 *   → `parseCliArgs` — parse the runner flags
 *   → `findExecutableOnPath` — locate `expect` and the requested tool on PATH
 *   → `buildIsolatedConfig` — normalize the copied config for deterministic runs
 *   → `runJsonPreflight` — detect obvious startup regressions before the PTY path
 *   → `runInteractiveTranscript` — execute the expect script and return the raw transcript
 *   → `main` — orchestrate the `/testfcm` workflow
 *
 * @see src/testfcm.js
 * @see task/TESTFCM-WORKFLOW.md
 */

import { accessSync, constants, copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import { stripVTControlCharacters } from 'node:util'
import { sources } from '../sources.js'
import {
  buildFixTasks,
  buildTestfcmReport,
  classifyToolTranscript,
  createTestfcmRunId,
  extractJsonPayload,
  hasConfiguredKey,
  pickTestfcmSelectionIndex,
  resolveTestfcmToolSpec,
} from '../src/testfcm.js'

const DEFAULTS = {
  tool: 'crush',
  prompt: 'hi',
  reportDir: 'task/reports',
  artifactDir: 'task/artifacts',
  toolBinDir: null,
  startupWaitMs: 8000,
  responseTimeoutMs: 20000,
  postEnterWaitMs: 3500,
  preflightTimeoutMs: 120000,
  terminalColumns: 220,
  terminalRows: 60,
}

function parseCliArgs(argv) {
  const options = { ...DEFAULTS, help: false }

  for (let idx = 2; idx < argv.length; idx++) {
    const arg = argv[idx]
    const next = argv[idx + 1]

    if (arg === '--help' || arg === '-h') {
      options.help = true
      continue
    }
    if (arg === '--tool' && next) {
      options.tool = next
      idx++
      continue
    }
    if (arg === '--prompt' && next) {
      options.prompt = next
      idx++
      continue
    }
    if (arg === '--report-dir' && next) {
      options.reportDir = next
      idx++
      continue
    }
    if (arg === '--artifact-dir' && next) {
      options.artifactDir = next
      idx++
      continue
    }
    if (arg === '--tool-bin-dir' && next) {
      options.toolBinDir = next
      idx++
      continue
    }
    if (arg === '--startup-wait-ms' && next) {
      options.startupWaitMs = Number.parseInt(next, 10) || DEFAULTS.startupWaitMs
      idx++
      continue
    }
    if (arg === '--response-timeout-ms' && next) {
      options.responseTimeoutMs = Number.parseInt(next, 10) || DEFAULTS.responseTimeoutMs
      idx++
      continue
    }
    if (arg === '--post-enter-wait-ms' && next) {
      options.postEnterWaitMs = Number.parseInt(next, 10) || DEFAULTS.postEnterWaitMs
      idx++
      continue
    }
    if (arg === '--preflight-timeout-ms' && next) {
      options.preflightTimeoutMs = Number.parseInt(next, 10) || DEFAULTS.preflightTimeoutMs
      idx++
      continue
    }
    if ((arg === '--term-columns' || arg === '--terminal-columns') && next) {
      options.terminalColumns = Number.parseInt(next, 10) || DEFAULTS.terminalColumns
      idx++
      continue
    }
    if ((arg === '--term-rows' || arg === '--terminal-rows') && next) {
      options.terminalRows = Number.parseInt(next, 10) || DEFAULTS.terminalRows
      idx++
      continue
    }
  }

  return options
}

function printHelp() {
  console.log(`
testfcm runner

Usage:
  node scripts/testfcm-runner.mjs [options]

Options:
  --tool <mode>                 Tool mode to launch (default: crush)
  --prompt <text>               Prompt sent after the tool opens (default: hi)
  --tool-bin-dir <path>         Prepend a custom bin directory to PATH
  --report-dir <path>           Report directory (default: task/reports)
  --artifact-dir <path>         Artifact directory (default: task/artifacts)
  --startup-wait-ms <ms>        Wait before pressing Enter in the TUI
  --post-enter-wait-ms <ms>     Wait after Enter before sending the prompt
  --response-timeout-ms <ms>    Max wait for a model reply
  --preflight-timeout-ms <ms>   Max wait for --json preflight
  --term-columns <n>            Target PTY width for expect (default: 220)
  --term-rows <n>               Target PTY height for expect (default: 60)
  --help, -h                    Show this help
`.trim())
}

function findExecutableOnPath(command, pathValue) {
  const paths = String(pathValue || '').split(':').filter(Boolean)
  for (const dir of paths) {
    const fullPath = join(dir, command)
    try {
      accessSync(fullPath, constants.X_OK)
      return fullPath
    } catch { /* keep searching */ }
  }
  return null
}

function normalizeTerminalText(text) {
  return stripVTControlCharacters(String(text || ''))
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\u0000/g, '')
}

function truncateForReport(text, maxChars = 4000) {
  const source = String(text || '')
  if (source.length <= maxChars) return source
  return `${source.slice(0, maxChars)}\n\n[truncated ${source.length - maxChars} chars]`
}

function writeArtifact(repoRoot, runDir, fileName, content) {
  const target = join(runDir, fileName)
  writeFileSync(target, String(content || ''), 'utf8')
  return target.startsWith(`${repoRoot}/`) ? target.slice(repoRoot.length + 1) : target
}

function copyArtifactIfExists(repoRoot, runDir, sourcePath, fileName) {
  if (!existsSync(sourcePath)) return null
  const target = join(runDir, fileName)
  copyFileSync(sourcePath, target)
  return target.startsWith(`${repoRoot}/`) ? target.slice(repoRoot.length + 1) : target
}

function buildIsolatedConfig(config, toolSpec) {
  const isolated = JSON.parse(JSON.stringify(config || {}))
  if (!isolated.apiKeys || typeof isolated.apiKeys !== 'object' || Array.isArray(isolated.apiKeys)) isolated.apiKeys = {}
  if (!isolated.providers || typeof isolated.providers !== 'object' || Array.isArray(isolated.providers)) isolated.providers = {}
  if (!isolated.settings || typeof isolated.settings !== 'object' || Array.isArray(isolated.settings)) isolated.settings = {}

  for (const providerKey of Object.keys(sources)) {
    const enabled = hasConfiguredKey(isolated.apiKeys[providerKey])
    isolated.providers[providerKey] = {
      ...(isolated.providers[providerKey] && typeof isolated.providers[providerKey] === 'object' ? isolated.providers[providerKey] : {}),
      enabled,
    }
  }

  isolated.favorites = []
  isolated.telemetry = {
    ...(isolated.telemetry && typeof isolated.telemetry === 'object' ? isolated.telemetry : {}),
    enabled: false,
  }
  isolated.settings = {
    ...isolated.settings,
    hideUnconfiguredModels: true,
    sortColumn: 'avg',
    sortAsc: true,
    preferredToolMode: toolSpec.mode,
  }

  return isolated
}

function runJsonPreflight(repoRoot, toolSpec, env, timeoutMs) {
  const cliPath = join(repoRoot, 'bin', 'free-coding-models.js')
  const result = spawnSync(process.execPath, [cliPath, '--json', toolSpec.flag, '--no-telemetry'], {
    cwd: repoRoot,
    env,
    encoding: 'utf8',
    timeout: timeoutMs,
  })

  const stdout = String(result.stdout || '')
  const stderr = String(result.stderr || '')
  const parsed = extractJsonPayload(stdout)

  if (result.status === 0 && parsed) {
    return {
      ok: true,
      stdout,
      stderr,
      summary: `JSON preflight succeeded and returned ${parsed.length} model rows.`,
      results: parsed,
    }
  }

  return {
    ok: false,
    stdout,
    stderr,
    summary: result.error
      ? `JSON preflight failed before PTY launch: ${result.error.message}`
      : `JSON preflight failed with exit code ${result.status ?? 'unknown'}.`,
    results: parsed,
  }
}

function runInteractiveTranscript(repoRoot, toolSpec, env, options) {
  const cliPath = join(repoRoot, 'bin', 'free-coding-models.js')
  const expectScript = `
    log_user 1
    set timeout -1
    proc send_repeated {sequence count delay_ms} {
      for {set i 0} {$i < $count} {incr i} {
        send -- $sequence
        after $delay_ms
      }
    }
    set startup_wait $env(TESTFCM_STARTUP_WAIT_MS)
    set post_enter_wait $env(TESTFCM_POST_ENTER_WAIT_MS)
    set response_wait $env(TESTFCM_RESPONSE_TIMEOUT_MS)
    set prompt_text $env(TESTFCM_PROMPT)
    set term_rows $env(TESTFCM_TERM_ROWS)
    set term_cols $env(TESTFCM_TERM_COLUMNS)
    set nav_up_count $env(TESTFCM_NAV_UP_COUNT)
    set nav_down_count $env(TESTFCM_NAV_DOWN_COUNT)

    catch { stty rows $term_rows columns $term_cols }

    spawn -noecho $env(TESTFCM_NODE) $env(TESTFCM_CLI) $env(TESTFCM_TOOL_FLAG) --disable-widths-warning --no-telemetry
    catch { stty rows $term_rows columns $term_cols < $spawn_out(slave,name) }

    after 1200 {
      send -- "\\033"
    }

    after $startup_wait {
      send_repeated "\\033[A" $nav_up_count 4
      after 120
      send_repeated "\\033[B" $nav_down_count 30
      after 180
      send -- "\\r"
    }

    after [expr {$startup_wait + 2200}] {
      send -- "\\r"
    }

    after [expr {$startup_wait + $post_enter_wait}] {
      send -- "$prompt_text\\r"
    }

    after [expr {$startup_wait + $post_enter_wait + $response_wait}] {
      send -- "\\003"
    }

    after [expr {$startup_wait + $post_enter_wait + $response_wait + 1200}] {
      send -- "\\003"
    }

    expect {
      eof {}
      -re {.+} { exp_continue }
    }
  `

  const result = spawnSync('expect', ['-c', expectScript], {
    cwd: repoRoot,
    env: {
      ...env,
      TESTFCM_NODE: process.execPath,
      TESTFCM_CLI: cliPath,
      TESTFCM_TOOL_FLAG: toolSpec.flag,
      TESTFCM_STARTUP_WAIT_MS: String(options.startupWaitMs),
      TESTFCM_POST_ENTER_WAIT_MS: String(options.postEnterWaitMs),
      TESTFCM_RESPONSE_TIMEOUT_MS: String(options.responseTimeoutMs),
      TESTFCM_PROMPT: options.prompt,
      TESTFCM_TERM_COLUMNS: String(options.terminalColumns),
      TESTFCM_TERM_ROWS: String(options.terminalRows),
      TESTFCM_NAV_UP_COUNT: '220',
      TESTFCM_NAV_DOWN_COUNT: String(options.selectionIndex || 0),
    },
    encoding: 'utf8',
    maxBuffer: 10 * 1024 * 1024,
    timeout: options.startupWaitMs + options.postEnterWaitMs + options.responseTimeoutMs + 15_000,
  })

  return {
    rawOutput: String(result.stdout || ''),
    stderr: String(result.stderr || ''),
    normalizedOutput: normalizeTerminalText(result.stdout || ''),
    status: result.status,
    error: result.error || null,
  }
}

async function main() {
  const options = parseCliArgs(process.argv)
  if (options.help) {
    printHelp()
    return
  }

  const toolSpec = resolveTestfcmToolSpec(options.tool)
  if (!toolSpec) {
    console.error(`Unknown --tool value "${options.tool}". Supported modes: ${Object.keys(sources).join(', ')}`)
    process.exitCode = 1
    return
  }

  const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
  const runId = createTestfcmRunId()
  const reportDir = resolve(repoRoot, options.reportDir)
  const artifactDir = resolve(repoRoot, options.artifactDir)
  const runDir = join(artifactDir, runId)
  const isolatedHome = join(runDir, 'home')
  const realHome = homedir()
  const realConfigPath = join(realHome, '.free-coding-models.json')
  const isolatedConfigPath = join(isolatedHome, '.free-coding-models.json')
  const startedAt = new Date().toISOString()
  const evidenceFiles = []
  const notes = []
  const findings = []

  let status = 'blocked'
  let preflightSummary = 'Preflight did not run.'
  let configuredProviders = []
  let toolBinaryPath = null
  let transcript = ''
  let requestLogSummary = []
  let selectionIndex = 0

  mkdirSync(reportDir, { recursive: true })
  mkdirSync(runDir, { recursive: true })
  mkdirSync(isolatedHome, { recursive: true })

  try {
    const effectivePath = options.toolBinDir
      ? `${resolve(repoRoot, options.toolBinDir)}:${process.env.PATH || ''}`
      : (process.env.PATH || '')

    const expectBinary = findExecutableOnPath('expect', effectivePath)
    if (!expectBinary) {
      findings.push({
        id: 'expect_missing',
        title: 'System PTY command `expect` is missing',
        severity: 'high',
        excerpt: 'expect',
        task: 'Install `expect` before running `/testfcm`, or use a machine where it is available.',
      })
      throw new Error('Could not find `expect` on PATH.')
    }

    if (!existsSync(realConfigPath)) {
      findings.push({
        id: 'missing_config',
        title: 'No FCM config found',
        severity: 'high',
        excerpt: realConfigPath,
        task: 'Create `~/.free-coding-models.json` with at least one provider key before running `/testfcm`.',
      })
      throw new Error(`Missing config file at ${realConfigPath}`)
    }

    const realConfig = JSON.parse(readFileSync(realConfigPath, 'utf8'))
    const isolatedConfig = buildIsolatedConfig(realConfig, toolSpec)
    configuredProviders = Object.keys(isolatedConfig.apiKeys || {}).filter((providerKey) => hasConfiguredKey(isolatedConfig.apiKeys[providerKey]))

    if (configuredProviders.length === 0) {
      findings.push({
        id: 'no_api_keys',
        title: 'No configured providers',
        severity: 'high',
        excerpt: 'apiKeys = {}',
        task: 'Add at least one working provider key before using `/testfcm`.',
      })
      throw new Error('The copied config does not contain any configured provider keys.')
    }

    writeFileSync(isolatedConfigPath, JSON.stringify(isolatedConfig, null, 2), { mode: 0o600 })
    const isolatedConfigArtifact = copyArtifactIfExists(repoRoot, runDir, isolatedConfigPath, 'isolated-config.json')
    if (isolatedConfigArtifact) evidenceFiles.push(isolatedConfigArtifact)

    toolBinaryPath = findExecutableOnPath(toolSpec.command, effectivePath)
    if (!toolBinaryPath) {
      notes.push(`The requested tool binary "${toolSpec.command}" was not found on the effective PATH before launch.`)
    }

    const childEnv = {
      ...process.env,
      HOME: isolatedHome,
      PATH: effectivePath,
      TERM: process.env.TERM || 'xterm-256color',
      LANG: process.env.LANG || 'en_US.UTF-8',
      LC_ALL: process.env.LC_ALL || 'en_US.UTF-8',
    }

    const preflight = runJsonPreflight(repoRoot, toolSpec, childEnv, options.preflightTimeoutMs)
    preflightSummary = preflight.summary
    evidenceFiles.push(writeArtifact(repoRoot, runDir, 'preflight-stdout.txt', preflight.stdout))
    if (preflight.stderr.trim()) {
      evidenceFiles.push(writeArtifact(repoRoot, runDir, 'preflight-stderr.txt', preflight.stderr))
    }
    if (!preflight.ok) {
      findings.push({
        id: 'json_preflight_failed',
        title: 'JSON preflight failed',
        severity: 'high',
        excerpt: truncateForReport(`${preflight.stdout}\n${preflight.stderr}`, 300),
        task: 'Fix the `--json` path or the startup failure before trusting `/testfcm` selection heuristics.',
      })
    } else {
      selectionIndex = pickTestfcmSelectionIndex(preflight.results, { preferProxy: false })
      options.selectionIndex = selectionIndex
      notes.push(`JSON preflight saw ${preflight.results?.length || 0} model rows before the PTY launch.`)
      notes.push(`Preflight-targeted row for Enter: #${selectionIndex + 1}.`)
    }

    const interactive = runInteractiveTranscript(repoRoot, toolSpec, childEnv, options)
    evidenceFiles.push(writeArtifact(repoRoot, runDir, 'tool-transcript.raw.txt', interactive.rawOutput))
    evidenceFiles.push(writeArtifact(repoRoot, runDir, 'tool-transcript.txt', interactive.normalizedOutput))
    if (interactive.stderr.trim()) {
      evidenceFiles.push(writeArtifact(repoRoot, runDir, 'tool-stderr.txt', interactive.stderr))
    }

    transcript = interactive.normalizedOutput

    for (const relativePath of toolSpec.configPaths) {
      const sourcePath = join(isolatedHome, relativePath)
      const fileName = relativePath.replace(/[\\/]+/g, '__')
      const copied = copyArtifactIfExists(repoRoot, runDir, sourcePath, fileName)
      if (copied) evidenceFiles.push(copied)
    }

    if (interactive.error) {
      findings.push({
        id: 'expect_runner_error',
        title: 'Expect session failed',
        severity: 'high',
        excerpt: interactive.error.message,
        task: 'Fix the PTY runner failure before trusting `/testfcm` output.',
      })
      status = 'blocked'
    } else {
      const transcriptResult = classifyToolTranscript(transcript)
      if (transcriptResult.status === 'passed') {
        status = 'passed'
        notes.push(`Success pattern matched: ${transcriptResult.matchedSuccess}`)
      } else if (transcriptResult.status === 'failed') {
        status = 'failed'
        findings.push(...transcriptResult.findings)
      } else {
        status = 'failed'
        findings.push({
          id: 'no_assistant_reply',
          title: 'No assistant reply matched the success heuristics',
          severity: 'high',
          excerpt: truncateForReport(transcript, 300),
          task: 'Inspect the tool transcript and request log to understand why the launched model never produced a usable reply.',
        })
      }
    }
  } catch (err) {
    if (findings.length === 0) {
      findings.push({
        id: 'runner_blocked',
        title: 'The `/testfcm` runner was blocked before completion',
        severity: 'high',
        excerpt: err.message,
        task: 'Fix the setup blocker, then re-run `/testfcm` to collect an end-to-end transcript.',
      })
    }
    notes.push(`Runner error: ${err.message}`)
  }

  const uniqueFindings = []
  const seenFindingIds = new Set()
  for (const finding of findings) {
    if (seenFindingIds.has(finding.id)) continue
    seenFindingIds.add(finding.id)
    uniqueFindings.push(finding)
  }

  const tasks = buildFixTasks(uniqueFindings)
  const finishedAt = new Date().toISOString()
  const report = buildTestfcmReport({
    runId,
    status,
    startedAt,
    finishedAt,
    toolLabel: toolSpec.label,
    toolMode: toolSpec.mode,
    prompt: options.prompt,
    configuredProviders,
    toolBinaryPath,
    isolatedHome,
    preflightSummary,
    findings: uniqueFindings,
    tasks,
    evidenceFiles,
    requestLogSummary,
    notes,
    transcriptExcerpt: truncateForReport(transcript, 4000),
  })

  const reportPath = join(reportDir, `testfcm-${runId}.md`)
  writeFileSync(reportPath, report, 'utf8')

  const reportDisplayPath = reportPath.startsWith(`${repoRoot}/`) ? reportPath.slice(repoRoot.length + 1) : reportPath
  console.log(`${status.toUpperCase()}: /testfcm finished`)
  console.log(`Report: ${reportDisplayPath}`)
  if (uniqueFindings.length > 0) {
    console.log('Findings:')
    for (const finding of uniqueFindings) {
      console.log(`- [${finding.severity}] ${finding.title}`)
    }
  } else {
    console.log('Findings: none')
  }

  if (status !== 'passed') {
    process.exitCode = 1
  }
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
