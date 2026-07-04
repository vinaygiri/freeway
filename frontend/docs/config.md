# Configuration Reference

## Config file

`~/.free-coding-models.json` is created automatically on first run (permissions `0600`).

```json
{
  "apiKeys": {
    "nvidia":      "nvapi-xxx",
    "groq":        "gsk_xxx",
    "cerebras":    "csk_xxx",
    "openrouter":  "sk-or-xxx",
    "huggingface": "hf_xxx",
    "replicate":   "r8_xxx",
    "deepinfra":   "di_xxx",
    "siliconflow": "sk_xxx",
    "together":    "together_xxx",
    "cloudflare":  "cf_xxx",
    "perplexity":  "pplx_xxx",
    "zai":         "zai-xxx"
  },
  "providers": {
    "nvidia":      { "enabled": true },
    "groq":        { "enabled": true },
    "cerebras":    { "enabled": true },
    "openrouter":  { "enabled": true },
    "huggingface": { "enabled": true },
    "replicate":   { "enabled": true },
    "deepinfra":   { "enabled": true },
    "siliconflow": { "enabled": true },
    "together":    { "enabled": true },
    "cloudflare":  { "enabled": true },
    "perplexity":  { "enabled": true },
    "zai":         { "enabled": true }
  },
  "settings": {
    "hideUnconfiguredModels": true
  },
  "router": {
    "enabled": true,
    "activeSet": "fast-coding",
    "port": 19280,
    "probeMode": "balanced",
    "sets": {
      "fast-coding": {
        "name": "fast-coding",
        "models": [
          { "provider": "groq", "model": "openai/gpt-oss-120b", "priority": 1 },
          { "provider": "cerebras", "model": "gpt-oss-120b", "priority": 2 }
        ],
        "created": "2026-04-22T10:00:00.000Z"
      }
    }
  },
  "favorites": [
    "nvidia/deepseek-ai/deepseek-v3.2"
  ]
}
```

---

## Environment variables

The TUI uses env vars before config values. The Smart Model Router daemon uses config keys first, then env vars as a fallback, because background services may not inherit your shell environment.

| Variable | Provider |
|----------|----------|
| `NVIDIA_API_KEY` | NVIDIA NIM |
| `GROQ_API_KEY` | Groq |
| `CEREBRAS_API_KEY` | Cerebras |
| `SAMBANOVA_API_KEY` | SambaNova |
| `OPENROUTER_API_KEY` | OpenRouter |
| `HUGGINGFACE_API_KEY` / `HF_TOKEN` | Hugging Face |
| `REPLICATE_API_TOKEN` | Replicate |
| `DEEPINFRA_API_KEY` / `DEEPINFRA_TOKEN` | DeepInfra |
| `CODESTRAL_API_KEY` | Mistral Codestral |
| `HYPERBOLIC_API_KEY` | Hyperbolic |
| `SCALEWAY_API_KEY` | Scaleway |
| `GOOGLE_API_KEY` | Google AI Studio |
| `SILICONFLOW_API_KEY` | SiliconFlow |
| `TOGETHER_API_KEY` | Together AI |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_API_KEY` | Cloudflare Workers AI |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare (required for endpoint URL) |
| `PERPLEXITY_API_KEY` / `PPLX_API_KEY` | Perplexity |
| `ZAI_API_KEY` | ZAI |
| `DASHSCOPE_API_KEY` | Alibaba Cloud (DashScope) |

---

## Runtime settings

| Setting | Default | Description |
|---------|---------|-------------|
| Ping timeout | 15 s | Per-request timeout. Slow models get more time. |
| Ping cadence | 2 s → 10 s → 30 s | Fast burst at startup, then normal, then idle slowdown |
| Configured-only | on | Only show providers with API keys. Toggle with `E`. |
| Favorites | persistent | Stored in config file, survive app restarts and updates |

---

## Smart Model Router

The router section is created automatically when you run `free-coding-models --daemon-bg` or `free-coding-models --daemon`. It controls the local OpenAI-compatible daemon.

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` until started | Whether router config is active. Starting the daemon enables it. |
| `port` | `19280` | Preferred localhost port. If occupied, the daemon scans `19280` through `19289`. |
| `activeSet` | `fast-coding` | Model set used by `/v1/chat/completions`. |
| `probeMode` | `balanced` | Health probe intensity: `eco`, `balanced`, or `aggressive`. |
| `sets` | auto-created | Named ordered model groups. Lower priority numbers are tried first during cold start. |

Each set model entry uses:

| Field | Description |
|-------|-------------|
| `provider` | Provider key from `sources.js`, such as `groq` or `nvidia`. |
| `model` | Provider-native model ID. |
| `priority` | User priority inside the set. The config normalizer keeps priorities contiguous. |

Runtime files:

| File | Purpose |
|------|---------|
| `~/.free-coding-models-daemon.pid` | Running daemon PID for stop/status discovery. |
| `~/.free-coding-models-daemon.port` | Actual port selected after fallback scanning. |
| `~/.free-coding-models-daemon.log` | Rotating daemon lifecycle, probe, and routing metadata logs. |
| `~/.free-coding-models-tokens.json` | Daily and all-time token counters from successful non-streaming responses. |
