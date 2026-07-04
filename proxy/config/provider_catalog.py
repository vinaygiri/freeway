"""Neutral provider catalog: IDs, credentials, defaults, proxy and capability metadata.

Adapter factories live in :mod:`providers.runtime.factory`; this module stays free of
provider implementation imports (see contract tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TransportType = Literal["openai_chat", "anthropic_messages"]

# Default upstream base URLs (also re-exported via :mod:`providers.defaults`)
NVIDIA_NIM_DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
# Moonshot Kimi Anthropic-compatible Messages API (POST …/messages).
KIMI_DEFAULT_BASE = "https://api.moonshot.ai/anthropic/v1"
WAFER_DEFAULT_BASE = "https://pass.wafer.ai/v1"
# DeepSeek Chat Completions API; cache usage is reported on this endpoint.
DEEPSEEK_DEFAULT_BASE = "https://api.deepseek.com"
FIREWORKS_DEFAULT_BASE = "https://api.fireworks.ai/inference/v1"
# Cloudflare account-scoped AI REST root; provider appends /accounts/{id}/ai/v1.
CLOUDFLARE_AI_REST_ROOT = "https://api.cloudflare.com/client/v4"
OPENROUTER_DEFAULT_BASE = "https://openrouter.ai/api/v1"
MISTRAL_DEFAULT_BASE = "https://api.mistral.ai/v1"
# Codestral IDE/personal endpoint (distinct from La Plateforme ``api.mistral.ai`` keys).
CODESTRAL_DEFAULT_BASE = "https://codestral.mistral.ai/v1"
LMSTUDIO_DEFAULT_BASE = "http://localhost:1234/v1"
LLAMACPP_DEFAULT_BASE = "http://localhost:8080/v1"
OLLAMA_DEFAULT_BASE = "http://localhost:11434"
OPENCODE_DEFAULT_BASE = "https://opencode.ai/zen/v1"
OPENCODE_GO_DEFAULT_BASE = "https://opencode.ai/zen/go/v1"
# Z.ai Anthropic-compatible Messages API (not OpenAI Coding Plan chat completions).
ZAI_DEFAULT_BASE = "https://api.z.ai/api/anthropic/v1"
# Google AI Studio Gemini API OpenAI-compat layer (not Vertex AI).
GEMINI_DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
GROQ_DEFAULT_BASE = "https://api.groq.com/openai/v1"
CEREBRAS_DEFAULT_BASE = "https://api.cerebras.ai/v1"
# Additional standard OpenAI-compatible free/free-tier providers (union with the
# free-coding-models catalog). All speak vanilla ``/chat/completions`` with Bearer
# auth, so they use the descriptor-driven GenericOpenAIChatProvider (default policy).
SAMBANOVA_DEFAULT_BASE = "https://api.sambanova.ai/v1"
NOVITA_DEFAULT_BASE = "https://api.novita.ai/openai/v1"
OVHCLOUD_DEFAULT_BASE = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
SCALEWAY_DEFAULT_BASE = "https://api.scaleway.ai/v1"
# Alibaba DashScope international OpenAI-compatible mode.
ALIBABA_DEFAULT_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
# GitHub Models inference root (OpenAI SDK appends /chat/completions).
GITHUB_MODELS_DEFAULT_BASE = "https://models.github.ai/inference"
OLLAMA_CLOUD_DEFAULT_BASE = "https://ollama.com/v1"
ROUTEWAY_DEFAULT_BASE = "https://api.routeway.ai/v1"


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    """Metadata for building :class:`~providers.base.ProviderConfig` and factory wiring."""

    provider_id: str
    display_name: str
    transport_type: TransportType
    capabilities: tuple[str, ...]
    credential_env: str | None = None
    credential_url: str | None = None
    credential_attr: str | None = None
    static_credential: str | None = None
    default_base_url: str | None = None
    base_url_attr: str | None = None
    proxy_attr: str | None = None


PROVIDER_CATALOG: dict[str, ProviderDescriptor] = {
    "nvidia_nim": ProviderDescriptor(
        provider_id="nvidia_nim",
        display_name="NVIDIA NIM",
        transport_type="openai_chat",
        credential_env="NVIDIA_NIM_API_KEY",
        credential_url="https://build.nvidia.com/settings/api-keys",
        credential_attr="nvidia_nim_api_key",
        default_base_url=NVIDIA_NIM_DEFAULT_BASE,
        proxy_attr="nvidia_nim_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "open_router": ProviderDescriptor(
        provider_id="open_router",
        display_name="OpenRouter",
        transport_type="anthropic_messages",
        credential_env="OPENROUTER_API_KEY",
        credential_url="https://openrouter.ai/keys",
        credential_attr="open_router_api_key",
        default_base_url=OPENROUTER_DEFAULT_BASE,
        proxy_attr="open_router_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
    "gemini": ProviderDescriptor(
        provider_id="gemini",
        display_name="Gemini",
        transport_type="openai_chat",
        credential_env="GEMINI_API_KEY",
        credential_url="https://aistudio.google.com/apikey",
        credential_attr="gemini_api_key",
        default_base_url=GEMINI_DEFAULT_BASE,
        proxy_attr="gemini_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "deepseek": ProviderDescriptor(
        provider_id="deepseek",
        display_name="DeepSeek",
        transport_type="openai_chat",
        credential_env="DEEPSEEK_API_KEY",
        credential_url="https://platform.deepseek.com/api_keys",
        credential_attr="deepseek_api_key",
        default_base_url=DEEPSEEK_DEFAULT_BASE,
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "mistral": ProviderDescriptor(
        provider_id="mistral",
        display_name="Mistral",
        transport_type="openai_chat",
        credential_env="MISTRAL_API_KEY",
        credential_url="https://console.mistral.ai/",
        credential_attr="mistral_api_key",
        default_base_url=MISTRAL_DEFAULT_BASE,
        proxy_attr="mistral_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "mistral_codestral": ProviderDescriptor(
        provider_id="mistral_codestral",
        display_name="Mistral Codestral",
        transport_type="openai_chat",
        credential_env="CODESTRAL_API_KEY",
        credential_url="https://console.mistral.ai/",
        credential_attr="codestral_api_key",
        default_base_url=CODESTRAL_DEFAULT_BASE,
        proxy_attr="codestral_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "opencode": ProviderDescriptor(
        provider_id="opencode",
        display_name="OpenCode Zen",
        transport_type="openai_chat",
        credential_env="OPENCODE_API_KEY",
        credential_url="https://opencode.ai/auth",
        credential_attr="opencode_api_key",
        default_base_url=OPENCODE_DEFAULT_BASE,
        proxy_attr="opencode_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "opencode_go": ProviderDescriptor(
        provider_id="opencode_go",
        display_name="OpenCode Go",
        transport_type="openai_chat",
        credential_env="OPENCODE_API_KEY",
        credential_url="https://opencode.ai/auth",
        credential_attr="opencode_api_key",
        default_base_url=OPENCODE_GO_DEFAULT_BASE,
        proxy_attr="opencode_go_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "wafer": ProviderDescriptor(
        provider_id="wafer",
        display_name="Wafer",
        transport_type="anthropic_messages",
        credential_env="WAFER_API_KEY",
        credential_url="https://www.wafer.ai/pass",
        credential_attr="wafer_api_key",
        default_base_url=WAFER_DEFAULT_BASE,
        proxy_attr="wafer_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
    "kimi": ProviderDescriptor(
        provider_id="kimi",
        display_name="Kimi",
        transport_type="anthropic_messages",
        credential_env="KIMI_API_KEY",
        credential_url="https://platform.moonshot.cn/console/api-keys",
        credential_attr="kimi_api_key",
        default_base_url=KIMI_DEFAULT_BASE,
        proxy_attr="kimi_proxy",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
        ),
    ),
    "cerebras": ProviderDescriptor(
        provider_id="cerebras",
        display_name="Cerebras",
        transport_type="openai_chat",
        credential_env="CEREBRAS_API_KEY",
        credential_url="https://cloud.cerebras.ai",
        credential_attr="cerebras_api_key",
        default_base_url=CEREBRAS_DEFAULT_BASE,
        proxy_attr="cerebras_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "groq": ProviderDescriptor(
        provider_id="groq",
        display_name="Groq",
        transport_type="openai_chat",
        credential_env="GROQ_API_KEY",
        credential_url="https://console.groq.com/keys",
        credential_attr="groq_api_key",
        default_base_url=GROQ_DEFAULT_BASE,
        proxy_attr="groq_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "fireworks": ProviderDescriptor(
        provider_id="fireworks",
        display_name="Fireworks",
        transport_type="anthropic_messages",
        credential_env="FIREWORKS_API_KEY",
        credential_url="https://fireworks.ai/account/api-keys",
        credential_attr="fireworks_api_key",
        default_base_url=FIREWORKS_DEFAULT_BASE,
        proxy_attr="fireworks_proxy",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
            "rate_limit",
        ),
    ),
    "cloudflare": ProviderDescriptor(
        provider_id="cloudflare",
        display_name="Cloudflare",
        transport_type="anthropic_messages",
        credential_env="CLOUDFLARE_API_TOKEN",
        credential_url="https://dash.cloudflare.com/profile/api-tokens",
        credential_attr="cloudflare_api_token",
        default_base_url=CLOUDFLARE_AI_REST_ROOT,
        proxy_attr="cloudflare_proxy",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
            "rate_limit",
        ),
    ),
    "zai": ProviderDescriptor(
        provider_id="zai",
        display_name="Z.ai",
        transport_type="anthropic_messages",
        credential_env="ZAI_API_KEY",
        credential_url="https://z.ai/manage-apikey/apikey-list",
        credential_attr="zai_api_key",
        default_base_url=ZAI_DEFAULT_BASE,
        proxy_attr="zai_proxy",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
            "rate_limit",
        ),
    ),
    "sambanova": ProviderDescriptor(
        provider_id="sambanova",
        display_name="SambaNova",
        transport_type="openai_chat",
        credential_env="SAMBANOVA_API_KEY",
        credential_url="https://cloud.sambanova.ai/apis",
        credential_attr="sambanova_api_key",
        default_base_url=SAMBANOVA_DEFAULT_BASE,
        proxy_attr="sambanova_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "novita": ProviderDescriptor(
        provider_id="novita",
        display_name="Novita AI",
        transport_type="openai_chat",
        credential_env="NOVITA_API_KEY",
        credential_url="https://novita.ai/settings/key-management",
        credential_attr="novita_api_key",
        default_base_url=NOVITA_DEFAULT_BASE,
        proxy_attr="novita_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "ovhcloud": ProviderDescriptor(
        provider_id="ovhcloud",
        display_name="OVHcloud AI Endpoints",
        transport_type="openai_chat",
        credential_env="OVHCLOUD_API_KEY",
        credential_url="https://endpoints.ai.cloud.ovh.net/",
        credential_attr="ovhcloud_api_key",
        default_base_url=OVHCLOUD_DEFAULT_BASE,
        proxy_attr="ovhcloud_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "scaleway": ProviderDescriptor(
        provider_id="scaleway",
        display_name="Scaleway Generative APIs",
        transport_type="openai_chat",
        credential_env="SCALEWAY_API_KEY",
        credential_url="https://console.scaleway.com/generative-apis/",
        credential_attr="scaleway_api_key",
        default_base_url=SCALEWAY_DEFAULT_BASE,
        proxy_attr="scaleway_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "alibaba": ProviderDescriptor(
        provider_id="alibaba",
        display_name="Alibaba DashScope",
        transport_type="openai_chat",
        credential_env="ALIBABA_API_KEY",
        credential_url="https://modelstudio.console.alibabacloud.com/",
        credential_attr="alibaba_api_key",
        default_base_url=ALIBABA_DEFAULT_BASE,
        proxy_attr="alibaba_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "github_models": ProviderDescriptor(
        provider_id="github_models",
        display_name="GitHub Models",
        transport_type="openai_chat",
        credential_env="GITHUB_MODELS_TOKEN",
        credential_url="https://github.com/settings/tokens",
        credential_attr="github_models_token",
        default_base_url=GITHUB_MODELS_DEFAULT_BASE,
        proxy_attr="github_models_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "ollama_cloud": ProviderDescriptor(
        provider_id="ollama_cloud",
        display_name="Ollama Cloud",
        transport_type="openai_chat",
        credential_env="OLLAMA_CLOUD_API_KEY",
        credential_url="https://ollama.com/settings/keys",
        credential_attr="ollama_cloud_api_key",
        default_base_url=OLLAMA_CLOUD_DEFAULT_BASE,
        proxy_attr="ollama_cloud_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "routeway": ProviderDescriptor(
        provider_id="routeway",
        display_name="Routeway",
        transport_type="openai_chat",
        credential_env="ROUTEWAY_API_KEY",
        credential_url="https://routeway.ai/",
        credential_attr="routeway_api_key",
        default_base_url=ROUTEWAY_DEFAULT_BASE,
        proxy_attr="routeway_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "lmstudio": ProviderDescriptor(
        provider_id="lmstudio",
        display_name="LM Studio",
        transport_type="anthropic_messages",
        static_credential="lm-studio",
        default_base_url=LMSTUDIO_DEFAULT_BASE,
        base_url_attr="lm_studio_base_url",
        proxy_attr="lmstudio_proxy",
        capabilities=("chat", "streaming", "tools", "native_anthropic", "local"),
    ),
    "llamacpp": ProviderDescriptor(
        provider_id="llamacpp",
        display_name="llama.cpp",
        transport_type="anthropic_messages",
        static_credential="llamacpp",
        default_base_url=LLAMACPP_DEFAULT_BASE,
        base_url_attr="llamacpp_base_url",
        proxy_attr="llamacpp_proxy",
        capabilities=("chat", "streaming", "tools", "native_anthropic", "local"),
    ),
    "ollama": ProviderDescriptor(
        provider_id="ollama",
        display_name="Ollama",
        transport_type="anthropic_messages",
        static_credential="ollama",
        default_base_url=OLLAMA_DEFAULT_BASE,
        base_url_attr="ollama_base_url",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
            "local",
        ),
    ),
}

# Key order:
# NVIDIA NIM first (README default), DeepSeek fourth, Wafer ninth / Kimi tenth; then cerebras /
# groq / fireworks / Cloudflare overlap; remainder and locals last per project plan (
# github.com/cheahjs/free-llm-api-resources Free Providers TOC as rough guide beyond fixed slots).
# ``SUPPORTED_PROVIDER_IDS`` inherits this insertion order for UI and error-message listing.
SUPPORTED_PROVIDER_IDS: tuple[str, ...] = tuple(PROVIDER_CATALOG.keys())

if len(set(SUPPORTED_PROVIDER_IDS)) != len(SUPPORTED_PROVIDER_IDS):
    raise AssertionError("Duplicate provider ids in PROVIDER_CATALOG key order")
