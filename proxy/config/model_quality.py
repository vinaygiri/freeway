"""Static model-quality catalog (tier / SWE-bench score / context window).

Generated from the free-coding-models catalog as a best-effort quality hint for
the admin Models view. Keyed by provider model id (first occurrence wins).
"""

from __future__ import annotations

# Tier scale (SWE-bench Verified): S+ >=70%, S 60-70, A+ 50-60, A 40-50,
# A- 35-40, B+ 30-35, B 20-30, C <20.
MODEL_QUALITY: dict[str, dict[str, str]] = {
    "@cf/google/gemma-4-26b-a4b-it": {
        "tier": "A-",
        "swe_score": "38.0%",
        "context": "128k",
    },
    "@cf/ibm/granite-4.0-h-micro": {
        "tier": "B+",
        "swe_score": "30.0%",
        "context": "128k",
    },
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {
        "tier": "A-",
        "swe_score": "39.5%",
        "context": "128k",
    },
    "@cf/meta/llama-4-scout-17b-16e-instruct": {
        "tier": "A",
        "swe_score": "44.0%",
        "context": "131k",
    },
    "@cf/mistralai/mistral-7b-instruct-v0.2": {
        "tier": "A",
        "swe_score": "38.0%",
        "context": "128k",
    },
    "@cf/mistralai/mistral-small-3.1-24b-instruct": {
        "tier": "B+",
        "swe_score": "30.0%",
        "context": "128k",
    },
    "@cf/moonshotai/kimi-k2.5": {"tier": "S+", "swe_score": "-", "context": "256k"},
    "@cf/moonshotai/kimi-k2.6": {"tier": "S+", "swe_score": "76.8%", "context": "262k"},
    "@cf/moonshotai/kimi-k2.7-code": {
        "tier": "S+",
        "swe_score": "-",
        "context": "262k",
    },
    "@cf/nvidia/nemotron-3-120b-a12b": {
        "tier": "A+",
        "swe_score": "56.0%",
        "context": "128k",
    },
    "@cf/openai/gpt-oss-120b": {"tier": "S", "swe_score": "60.0%", "context": "128k"},
    "@cf/openai/gpt-oss-20b": {"tier": "A", "swe_score": "42.0%", "context": "128k"},
    "@cf/qwen/qwen2.5-coder-32b-instruct": {
        "tier": "A",
        "swe_score": "46.0%",
        "context": "128k",
    },
    "@cf/qwen/qwen3-30b-a3b-fp8": {
        "tier": "A",
        "swe_score": "45.0%",
        "context": "128k",
    },
    "@cf/zai-org/glm-4.7-flash": {"tier": "S", "swe_score": "59.2%", "context": "131k"},
    "@cf/zai-org/glm-5.2": {"tier": "S+", "swe_score": "-", "context": "262k"},
    "DeepSeek-V3.1": {"tier": "S", "swe_score": "62.0%", "context": "128k"},
    "DeepSeek-V3.2": {"tier": "S+", "swe_score": "70.0%", "context": "32k"},
    "Meta-Llama-3.3-70B-Instruct": {
        "tier": "A-",
        "swe_score": "39.5%",
        "context": "128k",
    },
    "Meta-Llama-3_3-70B-Instruct": {
        "tier": "A-",
        "swe_score": "39.5%",
        "context": "131k",
    },
    "MiniMax-M2.7": {"tier": "S+", "swe_score": "56.2%", "context": "192k"},
    "Mistral-7B-Instruct-v0.3": {"tier": "B", "swe_score": "25.0%", "context": "127k"},
    "Mistral-Nemo-Instruct-2407": {
        "tier": "B+",
        "swe_score": "30.0%",
        "context": "118k",
    },
    "Mistral-Small-3.2-24B-Instruct-2506": {
        "tier": "B+",
        "swe_score": "34.0%",
        "context": "128k",
    },
    "Qwen3-32B": {"tier": "A+", "swe_score": "50.0%", "context": "32k"},
    "Qwen3-Coder-30B-A3B-Instruct": {
        "tier": "A+",
        "swe_score": "55.0%",
        "context": "256k",
    },
    "Qwen3-Embedding-8B": {"tier": "B", "swe_score": "-", "context": "-"},
    "Qwen3.5-397B-A17B": {"tier": "S", "swe_score": "-", "context": "262k"},
    "Qwen3.5-9B": {"tier": "B+", "swe_score": "30.0%", "context": "262k"},
    "Qwen3.6-27B": {"tier": "A", "swe_score": "-", "context": "262k"},
    "bge-m3": {"tier": "B", "swe_score": "-", "context": "-"},
    "bge-multilingual-gemma2": {"tier": "B", "swe_score": "-", "context": "-"},
    "big-pickle": {"tier": "S+", "swe_score": "72.0%", "context": "200k"},
    "bytedance/seed-oss-36b-instruct": {
        "tier": "A-",
        "swe_score": "38.0%",
        "context": "32k",
    },
    "codestral-2508": {"tier": "B+", "swe_score": "34.0%", "context": "128k"},
    "codestral-latest": {"tier": "B+", "swe_score": "34.0%", "context": "32k"},
    "cohere/north-mini-code:free": {"tier": "S", "swe_score": "-", "context": "256k"},
    "deepseek-ai/deepseek-v4-flash": {
        "tier": "S+",
        "swe_score": "72.0%",
        "context": "1M",
    },
    "deepseek-ai/deepseek-v4-pro": {
        "tier": "S+",
        "swe_score": "73.1%",
        "context": "1M",
    },
    "deepseek-v4-flash": {"tier": "S+", "swe_score": "-", "context": "128k"},
    "deepseek-v4-flash-free": {"tier": "S+", "swe_score": "79.0%", "context": "200k"},
    "deepseek-v4-flash:free": {"tier": "S+", "swe_score": "72.0%", "context": "1M"},
    "deepseek-v4-pro": {"tier": "S+", "swe_score": "73.1%", "context": "1M"},
    "deepseek/deepseek-v3-0324": {"tier": "S", "swe_score": "62.0%", "context": "128k"},
    "devstral-2-123b-instruct-2512": {
        "tier": "S+",
        "swe_score": "72.2%",
        "context": "200k",
    },
    "devstral-2512": {"tier": "S+", "swe_score": "72.2%", "context": "256k"},
    "devstral-2:123b": {"tier": "S+", "swe_score": "72.2%", "context": "200k"},
    "devstral-small-2:24b": {"tier": "A", "swe_score": "-", "context": "128k"},
    "gemini-2.5-flash": {"tier": "A+", "swe_score": "50.0%", "context": "1M"},
    "gemini-2.5-flash-lite": {"tier": "A", "swe_score": "42.0%", "context": "1M"},
    "gemini-2.5-pro": {"tier": "S+", "swe_score": "63.2%", "context": "1M"},
    "gemini-3-flash-preview": {"tier": "S", "swe_score": "65.0%", "context": "1M"},
    "gemini-3.1-flash-lite": {"tier": "A+", "swe_score": "55.0%", "context": "1M"},
    "gemini-3.1-pro-preview": {"tier": "S+", "swe_score": "78.0%", "context": "1M"},
    "gemini-3.5-flash": {"tier": "S+", "swe_score": "-", "context": "1M"},
    "gemma-3-27b-it": {"tier": "B", "swe_score": "22.0%", "context": "40k"},
    "gemma-4-31B-it": {"tier": "A", "swe_score": "45.0%", "context": "128k"},
    "gemma-4-31b-it:free": {"tier": "A", "swe_score": "45.0%", "context": "262k"},
    "gemma4:31b": {"tier": "A", "swe_score": "45.0%", "context": "256k"},
    "glm-4.7": {"tier": "S+", "swe_score": "73.8%", "context": "128k"},
    "glm-5.1": {"tier": "S+", "swe_score": "77.8%", "context": "203k"},
    "google/gemma-4-26b-a4b-it:free": {
        "tier": "A",
        "swe_score": "38.0%",
        "context": "262k",
    },
    "google/gemma-4-31b-it": {"tier": "A", "swe_score": "45.0%", "context": "256k"},
    "google/gemma-4-31b-it:free": {
        "tier": "A",
        "swe_score": "45.0%",
        "context": "262k",
    },
    "gpt-oss-120b": {"tier": "S", "swe_score": "60.0%", "context": "131k"},
    "gpt-oss-120b:free": {"tier": "S", "swe_score": "60.0%", "context": "131k"},
    "gpt-oss-20b": {"tier": "A", "swe_score": "42.0%", "context": "131k"},
    "gpt-oss:120b": {"tier": "S", "swe_score": "60.0%", "context": "128k"},
    "gpt-oss:20b": {"tier": "A", "swe_score": "42.0%", "context": "128k"},
    "groq/compound": {"tier": "A", "swe_score": "45.0%", "context": "131k"},
    "groq/compound-mini": {"tier": "B+", "swe_score": "32.0%", "context": "131k"},
    "holo2-30b-a3b": {"tier": "A+", "swe_score": "52.0%", "context": "22k"},
    "kilo-auto/free": {"tier": "A+", "swe_score": "-", "context": "256k"},
    "kimi-k2.6": {"tier": "S+", "swe_score": "-", "context": "256k"},
    "laguna-m.1:free": {"tier": "S+", "swe_score": "-", "context": "131k"},
    "laguna-xs.2:free": {"tier": "S+", "swe_score": "-", "context": "131k"},
    "ling-2.6-flash:free": {"tier": "S", "swe_score": "-", "context": "262k"},
    "llama-3.1-8b-instant": {"tier": "B", "swe_score": "28.8%", "context": "131k"},
    "llama-3.1-8b-instruct:free": {"tier": "B", "swe_score": "28.8%", "context": "16k"},
    "llama-3.2-1b-instruct:free": {"tier": "C", "swe_score": "-", "context": "16k"},
    "llama-3.2-3b-instruct:free": {"tier": "B", "swe_score": "20.0%", "context": "16k"},
    "llama-3.3-70b-instruct": {"tier": "A-", "swe_score": "39.5%", "context": "100k"},
    "llama-3.3-70b-instruct:free": {
        "tier": "A-",
        "swe_score": "39.5%",
        "context": "131k",
    },
    "llama-3.3-70b-versatile": {"tier": "A-", "swe_score": "39.5%", "context": "131k"},
    "magistral-medium-2509": {"tier": "A+", "swe_score": "52.0%", "context": "128k"},
    "meta-llama/llama-4-scout-17b-16e-instruct": {
        "tier": "A",
        "swe_score": "44.0%",
        "context": "131k",
    },
    "meta/llama-3.2-11b-vision-instruct": {
        "tier": "B",
        "swe_score": "28.0%",
        "context": "128k",
    },
    "meta/llama-3.2-90b-vision-instruct": {
        "tier": "A-",
        "swe_score": "-",
        "context": "128k",
    },
    "meta/llama-3.3-70b-instruct": {
        "tier": "A-",
        "swe_score": "39.5%",
        "context": "128k",
    },
    "meta/llama-4-maverick-17b-128e-instruct": {
        "tier": "S",
        "swe_score": "62.0%",
        "context": "1M",
    },
    "meta/llama-4-maverick-17b-128e-instruct-fp8": {
        "tier": "S",
        "swe_score": "62.0%",
        "context": "1M",
    },
    "meta/llama-4-scout-17b-16e-instruct": {
        "tier": "A",
        "swe_score": "44.0%",
        "context": "1M",
    },
    "meta/meta-llama-3.1-405b-instruct": {
        "tier": "A",
        "swe_score": "44.0%",
        "context": "128k",
    },
    "meta/meta-llama-3.1-8b-instruct": {
        "tier": "B",
        "swe_score": "28.8%",
        "context": "128k",
    },
    "microsoft/phi-4-mini-instruct": {
        "tier": "C",
        "swe_score": "14.0%",
        "context": "128k",
    },
    "mimo-v2.5-free": {"tier": "S+", "swe_score": "-", "context": "200k"},
    "minimax-m2.7": {"tier": "S+", "swe_score": "80.2%", "context": "200k"},
    "minimax-m2:free": {"tier": "S", "swe_score": "-", "context": "197k"},
    "minimax-m3": {"tier": "S", "swe_score": "59.0%", "context": "1M"},
    "minimax/m2-her": {"tier": "S", "swe_score": "-", "context": "32k"},
    "minimaxai/minimax-m2.7": {"tier": "S+", "swe_score": "80.2%", "context": "200k"},
    "minimaxai/minimax-m3": {"tier": "S", "swe_score": "59.0%", "context": "1M"},
    "mistral-ai/codestral-2501": {
        "tier": "B+",
        "swe_score": "34.0%",
        "context": "256k",
    },
    "mistral-ai/ministral-3b": {"tier": "C", "swe_score": "-", "context": "128k"},
    "mistral-ai/mistral-medium-2505": {
        "tier": "A",
        "swe_score": "48.0%",
        "context": "128k",
    },
    "mistral-ai/mistral-small-2503": {
        "tier": "B+",
        "swe_score": "30.0%",
        "context": "128k",
    },
    "mistral-large-2512": {"tier": "S+", "swe_score": "70.0%", "context": "256k"},
    "mistral-large-3:675b": {"tier": "A+", "swe_score": "58.0%", "context": "256k"},
    "mistral-medium-3-5": {"tier": "S+", "swe_score": "77.6%", "context": "256k"},
    "mistral-nemo-instruct:free": {
        "tier": "B+",
        "swe_score": "30.0%",
        "context": "16k",
    },
    "mistral-small-2603": {"tier": "A", "swe_score": "48.0%", "context": "256k"},
    "mistral-small-3.2": {"tier": "B+", "swe_score": "34.0%", "context": "128k"},
    "mistral-small-3.2-24b-instruct-2506": {
        "tier": "B+",
        "swe_score": "30.0%",
        "context": "128k",
    },
    "mistral/mistral-large-3-675b-instruct-2512": {
        "tier": "A+",
        "swe_score": "58.0%",
        "context": "250k",
    },
    "mistralai/ministral-14b-instruct-2512": {
        "tier": "B+",
        "swe_score": "34.0%",
        "context": "32k",
    },
    "mistralai/mistral-large-3-675b-instruct-2512": {
        "tier": "A+",
        "swe_score": "58.0%",
        "context": "256k",
    },
    "mistralai/mistral-medium-3.5-128b": {
        "tier": "S",
        "swe_score": "66.0%",
        "context": "128k",
    },
    "mistralai/mistral-small-4-119b-2603": {
        "tier": "S",
        "swe_score": "60.0%",
        "context": "256k",
    },
    "moonshotai/kimi-k2.6": {"tier": "S+", "swe_score": "76.8%", "context": "256k"},
    "nemotron-3-nano-30b-a3b:free": {
        "tier": "A",
        "swe_score": "43.0%",
        "context": "256k",
    },
    "nemotron-3-super": {"tier": "A+", "swe_score": "56.0%", "context": "128k"},
    "nemotron-3-ultra": {"tier": "S+", "swe_score": "-", "context": "1M"},
    "nemotron-3-ultra-free": {"tier": "A+", "swe_score": "-", "context": "200k"},
    "nemotron-nano-9b-v2:free": {"tier": "B+", "swe_score": "18.0%", "context": "128k"},
    "nex-agi/nex-n2-pro": {"tier": "S", "swe_score": "-", "context": "262k"},
    "north-mini-code-free": {"tier": "B+", "swe_score": "-", "context": "200k"},
    "nvidia/nemotron-3-nano-30b-a3b": {
        "tier": "A",
        "swe_score": "43.0%",
        "context": "128k",
    },
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": {
        "tier": "A+",
        "swe_score": "52.0%",
        "context": "128k",
    },
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": {
        "tier": "A+",
        "swe_score": "52.0%",
        "context": "256k",
    },
    "nvidia/nemotron-3-super-120b-a12b": {
        "tier": "A+",
        "swe_score": "56.0%",
        "context": "128k",
    },
    "nvidia/nemotron-3-super-120b-a12b:free": {
        "tier": "A+",
        "swe_score": "56.0%",
        "context": "1M",
    },
    "nvidia/nemotron-3-ultra-550b-a55b": {
        "tier": "S+",
        "swe_score": "-",
        "context": "1M",
    },
    "nvidia/nemotron-3-ultra-550b-a55b:free": {
        "tier": "S+",
        "swe_score": "-",
        "context": "1M",
    },
    "nvidia/nemotron-nano-12b-v2-vl:free": {
        "tier": "A",
        "swe_score": "20.0%",
        "context": "128k",
    },
    "nvidia/nemotron-nano-30b-a3b:free": {
        "tier": "A",
        "swe_score": "43.0%",
        "context": "256k",
    },
    "nvidia/nemotron-nano-9b-v2:free": {
        "tier": "B+",
        "swe_score": "18.0%",
        "context": "128k",
    },
    "openai/gpt-4.1": {"tier": "S+", "swe_score": "-", "context": "1M"},
    "openai/gpt-4.1-mini": {"tier": "S", "swe_score": "-", "context": "1M"},
    "openai/gpt-4.1-nano": {"tier": "A", "swe_score": "-", "context": "1M"},
    "openai/gpt-oss-120b": {"tier": "S", "swe_score": "60.0%", "context": "128k"},
    "openai/gpt-oss-120b:free": {"tier": "S", "swe_score": "60.0%", "context": "131k"},
    "openai/gpt-oss-20b": {"tier": "A", "swe_score": "42.0%", "context": "128k"},
    "openai/gpt-oss-20b:free": {"tier": "A", "swe_score": "42.0%", "context": "131k"},
    "openrouter/free": {"tier": "B", "swe_score": "-", "context": "200k"},
    "openrouter/owl-alpha": {"tier": "A+", "swe_score": "-", "context": "1M"},
    "poolside/laguna-m.1:free": {"tier": "S+", "swe_score": "-", "context": "262k"},
    "poolside/laguna-xs.2:free": {"tier": "S+", "swe_score": "-", "context": "262k"},
    "qwen/qwen3-32b": {"tier": "A+", "swe_score": "50.0%", "context": "131k"},
    "qwen/qwen3-next-80b-a3b-instruct": {
        "tier": "S",
        "swe_score": "65.0%",
        "context": "128k",
    },
    "qwen/qwen3.5-122b-a10b": {"tier": "S", "swe_score": "64.0%", "context": "128k"},
    "qwen/qwen3.5-397b-a17b": {"tier": "S", "swe_score": "68.0%", "context": "128k"},
    "qwen/qwen3.5-plus": {"tier": "S", "swe_score": "68.0%", "context": "1M"},
    "qwen/qwen3.6-27b": {"tier": "A", "swe_score": "-", "context": "131k"},
    "qwen/qwen3.6-plus": {"tier": "S+", "swe_score": "72.0%", "context": "1M"},
    "qwen3-235b": {"tier": "S+", "swe_score": "70.0%", "context": "240k"},
    "qwen3-235b-a22b": {"tier": "S+", "swe_score": "70.0%", "context": "256k"},
    "qwen3-235b-a22b-instruct-2507": {
        "tier": "S+",
        "swe_score": "70.0%",
        "context": "250k",
    },
    "qwen3-32b": {"tier": "A+", "swe_score": "50.0%", "context": "256k"},
    "qwen3-coder-30b-a3b-instruct": {
        "tier": "A+",
        "swe_score": "55.0%",
        "context": "128k",
    },
    "qwen3-coder-flash": {"tier": "A+", "swe_score": "55.0%", "context": "1M"},
    "qwen3-coder-next": {"tier": "S", "swe_score": "65.0%", "context": "256k"},
    "qwen3-coder-plus": {"tier": "S", "swe_score": "69.6%", "context": "1M"},
    "qwen3-coder:480b": {"tier": "S+", "swe_score": "70.6%", "context": "256k"},
    "qwen3-max": {"tier": "S+", "swe_score": "78.8%", "context": "256k"},
    "qwen3.5-397b-a17b": {"tier": "S", "swe_score": "68.0%", "context": "250k"},
    "qwen3.5-flash": {"tier": "A+", "swe_score": "55.0%", "context": "1M"},
    "qwen3.5-plus": {"tier": "S", "swe_score": "68.0%", "context": "1M"},
    "qwen3.5:397b": {"tier": "S", "swe_score": "68.0%", "context": "128k"},
    "qwen3.6-35b-a3b": {"tier": "A+", "swe_score": "-", "context": "256k"},
    "qwen3.6-flash": {"tier": "A+", "swe_score": "60.0%", "context": "1M"},
    "qwen3.6-plus": {"tier": "S+", "swe_score": "72.0%", "context": "1M"},
    "qwen3.7-max": {"tier": "S+", "swe_score": "80.0%", "context": "1M"},
    "step-3.5-flash:free": {"tier": "S+", "swe_score": "74.4%", "context": "256k"},
    "stepfun-ai/step-3.5-flash": {
        "tier": "S+",
        "swe_score": "74.4%",
        "context": "256k",
    },
    "stepfun-ai/step-3.7-flash": {
        "tier": "S+",
        "swe_score": "74.4%",
        "context": "256k",
    },
    "stockmark/stockmark-2-100b-instruct": {
        "tier": "A-",
        "swe_score": "36.0%",
        "context": "32k",
    },
    "z-ai/glm-5.1": {"tier": "S+", "swe_score": "77.8%", "context": "128k"},
    "zai-glm-4.7": {"tier": "S+", "swe_score": "73.8%", "context": "131k"},
    "zai/glm-4.5-flash": {"tier": "S", "swe_score": "59.2%", "context": "128k"},
    "zai/glm-4.7-flash": {"tier": "S", "swe_score": "59.2%", "context": "200k"},
}

_LOWER = {k.lower(): v for k, v in MODEL_QUALITY.items()}


def quality_for(model_id: str) -> dict[str, str] | None:
    """Return quality tags for a model id (case-insensitive), or None."""
    return MODEL_QUALITY.get(model_id) or _LOWER.get(model_id.lower())


def parse_context_tokens(context: str) -> int | None:
    """Parse a catalog context string ('128k', '1M', '8192') into an int token count."""
    text = context.strip().lower().replace("tokens", "").strip()
    if not text or text == "-":
        return None
    multiplier = 1
    if text.endswith("k"):
        multiplier, text = 1_000, text[:-1]
    elif text.endswith("m"):
        multiplier, text = 1_000_000, text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None


def context_tokens_for(model_id: str) -> int | None:
    """Return a model's advertised context window in tokens, or None if unknown."""
    quality = quality_for(model_id)
    if not quality:
        return None
    context = quality.get("context")
    return parse_context_tokens(context) if context else None
