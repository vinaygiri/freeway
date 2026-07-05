"""Flat application settings schema loaded by Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import HTTP_CONNECT_TIMEOUT_DEFAULT
from .env_files import (
    ANTHROPIC_AUTH_TOKEN_ENV,
    env_file_override,
    settings_env_files,
)
from .nim import NimSettings
from .provider_ids import SUPPORTED_PROVIDER_IDS


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==================== OpenRouter Config ====================
    open_router_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")

    # ==================== Mistral La Plateforme ====================
    mistral_api_key: str = Field(default="", validation_alias="MISTRAL_API_KEY")

    # ==================== Mistral Codestral (codestral.mistral.ai) ====================
    codestral_api_key: str = Field(default="", validation_alias="CODESTRAL_API_KEY")

    # ==================== DeepSeek Config ====================
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")

    # ==================== Kimi Config ====================
    kimi_api_key: str = Field(default="", validation_alias="KIMI_API_KEY")

    # ==================== Wafer Config ====================
    wafer_api_key: str = Field(default="", validation_alias="WAFER_API_KEY")

    # ==================== OpenCode Zen / OpenCode Go ====================
    # Same key from opencode.ai/auth; zen uses prefix ``opencode/``, Go uses ``opencode_go/``.
    opencode_api_key: str = Field(default="", validation_alias="OPENCODE_API_KEY")

    # ==================== Z.ai Config ====================
    zai_api_key: str = Field(default="", validation_alias="ZAI_API_KEY")

    # ==================== Fireworks AI Config ====================
    fireworks_api_key: str = Field(default="", validation_alias="FIREWORKS_API_KEY")

    # ==================== Cloudflare AI REST Config ====================
    cloudflare_api_token: str = Field(
        default="", validation_alias="CLOUDFLARE_API_TOKEN"
    )
    cloudflare_account_id: str = Field(
        default="", validation_alias="CLOUDFLARE_ACCOUNT_ID"
    )

    # ==================== Google Gemini (Google AI Studio) ====================
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")

    # ==================== Groq (OpenAI-compatible) ====================
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    # ==================== Cerebras Inference (OpenAI-compatible) ====================
    cerebras_api_key: str = Field(default="", validation_alias="CEREBRAS_API_KEY")

    # ========= Additional standard OpenAI-compatible free/free-tier providers =========
    sambanova_api_key: str = Field(default="", validation_alias="SAMBANOVA_API_KEY")
    novita_api_key: str = Field(default="", validation_alias="NOVITA_API_KEY")
    ovhcloud_api_key: str = Field(default="", validation_alias="OVHCLOUD_API_KEY")
    scaleway_api_key: str = Field(default="", validation_alias="SCALEWAY_API_KEY")
    alibaba_api_key: str = Field(default="", validation_alias="ALIBABA_API_KEY")
    github_models_token: str = Field(default="", validation_alias="GITHUB_MODELS_TOKEN")
    ollama_cloud_api_key: str = Field(
        default="", validation_alias="OLLAMA_CLOUD_API_KEY"
    )
    routeway_api_key: str = Field(default="", validation_alias="ROUTEWAY_API_KEY")

    # ==================== Messaging Platform Selection ====================
    # Valid: "telegram" | "discord" | "none"
    messaging_platform: str = Field(
        default="discord", validation_alias="MESSAGING_PLATFORM"
    )
    messaging_rate_limit: int = Field(
        default=1, validation_alias="MESSAGING_RATE_LIMIT"
    )
    messaging_rate_window: float = Field(
        default=1.0, validation_alias="MESSAGING_RATE_WINDOW"
    )

    # ==================== NVIDIA NIM Config ====================
    nvidia_nim_api_key: str = ""

    # ==================== LM Studio Config ====================
    lm_studio_base_url: str = Field(
        default="http://localhost:1234/v1",
        validation_alias="LM_STUDIO_BASE_URL",
    )

    # ==================== Llama.cpp Config ====================
    llamacpp_base_url: str = Field(
        default="http://localhost:8080/v1",
        validation_alias="LLAMACPP_BASE_URL",
    )

    # ==================== Ollama Config ====================
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )

    # ==================== Model Fallbacks (failover chain) ====================
    # Comma-separated provider/model refs tried, in order, when the primary
    # model's provider is unavailable / rate-limited / circuit-open.
    model_fallbacks: str = Field(default="", validation_alias="MODEL_FALLBACKS")

    # ==================== Inline Model Directives (@-mentions) ====================
    # Alias table: "key=provider/model, key2=provider/model". Mentioning ``@key``
    # (or ``@provider/model`` directly) in a prompt routes that request there.
    model_directives: str = Field(default="", validation_alias="MODEL_DIRECTIVES")

    # ==================== Model ====================
    # All Claude model requests are mapped to this single model (fallback)
    # Format: provider_type/model/name
    model: str = "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"

    # Per-model overrides (optional, falls back to MODEL)
    # Each can use a different provider
    model_opus: str | None = Field(default=None, validation_alias="MODEL_OPUS")
    model_sonnet: str | None = Field(default=None, validation_alias="MODEL_SONNET")
    model_haiku: str | None = Field(default=None, validation_alias="MODEL_HAIKU")

    # ==================== Claude Code client behavior ====================
    # Token budget Claude Code assumes before auto-compacting the conversation.
    # Default is sized for Anthropic 200k-context models; lower it for smaller
    # free models (via CLAUDE_CODE_AUTO_COMPACT_WINDOW) so long sessions compact
    # instead of growing until the upstream rejects the request.
    claude_code_auto_compact_window: int = Field(
        default=190000, validation_alias="CLAUDE_CODE_AUTO_COMPACT_WINDOW"
    )

    # Comma-separated tool-name patterns (fnmatch globs, e.g. "Workflow,Task*,
    # Cron*") to strip from inbound Messages requests before forwarding upstream.
    # Client tools like Claude Code attach every tool's full JSON schema to every
    # request; on small free-tier token budgets those schemas alone can exceed the
    # per-minute limit. Dropping unused ones shrinks the request. Empty = keep all.
    drop_tools: str = Field(default="", validation_alias="DROP_TOOLS")

    # Auto-fit: when an inbound Messages request exceeds this budget, drop the
    # largest non-essential tool schemas (keeping AUTO_FIT_KEEP_TOOLS) and then the
    # oldest whole turns until it fits — so a request that would 413/400 on a small
    # free tier is trimmed to fit instead of failing.
    #   > 0  explicit budget (set to your provider's real per-request limit)
    #   = 0  auto: 90% of the routed model's advertised context (default; only
    #        trims requests that would exceed the model's own window, so working
    #        requests are untouched)
    #   < 0  disabled
    auto_fit_max_tokens: int = Field(default=0, validation_alias="AUTO_FIT_MAX_TOKENS")
    auto_fit_keep_tools: str = Field(
        default=(
            "Bash,Read,Edit,Write,Glob,Grep,LS,MultiEdit,NotebookEdit,"
            "WebFetch,WebSearch,TodoWrite"
        ),
        validation_alias="AUTO_FIT_KEEP_TOOLS",
    )

    # Comma-separated provider/model refs you've starred in the Models view. Used by
    # the admin UI's "Use only favourites" action to build the primary + fallback chain.
    favourite_models: str = Field(default="", validation_alias="FAVOURITE_MODELS")

    # ==================== Per-Provider Proxy ====================
    nvidia_nim_proxy: str = Field(default="", validation_alias="NVIDIA_NIM_PROXY")
    open_router_proxy: str = Field(default="", validation_alias="OPENROUTER_PROXY")
    mistral_proxy: str = Field(default="", validation_alias="MISTRAL_PROXY")
    codestral_proxy: str = Field(default="", validation_alias="CODESTRAL_PROXY")
    lmstudio_proxy: str = Field(default="", validation_alias="LMSTUDIO_PROXY")
    llamacpp_proxy: str = Field(default="", validation_alias="LLAMACPP_PROXY")
    kimi_proxy: str = Field(default="", validation_alias="KIMI_PROXY")
    wafer_proxy: str = Field(default="", validation_alias="WAFER_PROXY")
    opencode_proxy: str = Field(default="", validation_alias="OPENCODE_PROXY")
    opencode_go_proxy: str = Field(default="", validation_alias="OPENCODE_GO_PROXY")
    zai_proxy: str = Field(default="", validation_alias="ZAI_PROXY")
    fireworks_proxy: str = Field(default="", validation_alias="FIREWORKS_PROXY")
    cloudflare_proxy: str = Field(default="", validation_alias="CLOUDFLARE_PROXY")
    gemini_proxy: str = Field(default="", validation_alias="GEMINI_PROXY")
    groq_proxy: str = Field(default="", validation_alias="GROQ_PROXY")
    cerebras_proxy: str = Field(default="", validation_alias="CEREBRAS_PROXY")
    sambanova_proxy: str = Field(default="", validation_alias="SAMBANOVA_PROXY")
    novita_proxy: str = Field(default="", validation_alias="NOVITA_PROXY")
    ovhcloud_proxy: str = Field(default="", validation_alias="OVHCLOUD_PROXY")
    scaleway_proxy: str = Field(default="", validation_alias="SCALEWAY_PROXY")
    alibaba_proxy: str = Field(default="", validation_alias="ALIBABA_PROXY")
    github_models_proxy: str = Field(default="", validation_alias="GITHUB_MODELS_PROXY")
    ollama_cloud_proxy: str = Field(default="", validation_alias="OLLAMA_CLOUD_PROXY")
    routeway_proxy: str = Field(default="", validation_alias="ROUTEWAY_PROXY")

    # ==================== Provider Rate Limiting ====================
    provider_rate_limit: int = Field(default=40, validation_alias="PROVIDER_RATE_LIMIT")
    provider_rate_window: int = Field(
        default=60, validation_alias="PROVIDER_RATE_WINDOW"
    )
    provider_max_concurrency: int = Field(
        default=5, validation_alias="PROVIDER_MAX_CONCURRENCY"
    )
    enable_model_thinking: bool = Field(
        default=True, validation_alias="ENABLE_MODEL_THINKING"
    )
    enable_opus_thinking: bool | None = Field(
        default=None, validation_alias="ENABLE_OPUS_THINKING"
    )
    enable_sonnet_thinking: bool | None = Field(
        default=None, validation_alias="ENABLE_SONNET_THINKING"
    )
    enable_haiku_thinking: bool | None = Field(
        default=None, validation_alias="ENABLE_HAIKU_THINKING"
    )

    # ==================== Health Probes ====================
    enable_health_probes: bool = Field(
        default=True, validation_alias="ENABLE_HEALTH_PROBES"
    )
    health_probe_interval_seconds: int = Field(
        default=60, validation_alias="HEALTH_PROBE_INTERVAL_SECONDS"
    )
    health_probe_sample_window: int = Field(
        default=100, validation_alias="HEALTH_PROBE_SAMPLE_WINDOW"
    )

    # ==================== Quota Governor ====================
    enable_quota_tracking: bool = Field(
        default=True, validation_alias="ENABLE_QUOTA_TRACKING"
    )

    # ==================== Request Inspector ====================
    enable_request_inspector: bool = Field(
        default=True, validation_alias="ENABLE_REQUEST_INSPECTOR"
    )
    request_inspector_window: int = Field(
        default=200, validation_alias="REQUEST_INSPECTOR_WINDOW"
    )

    # ==================== Response Cache ====================
    # Opt-in exact-match cache; only no-tool + temperature==0 requests are cached.
    enable_response_cache: bool = Field(
        default=False, validation_alias="ENABLE_RESPONSE_CACHE"
    )
    response_cache_window: int = Field(
        default=256, validation_alias="RESPONSE_CACHE_WINDOW"
    )
    response_cache_ttl_seconds: int = Field(
        default=300, validation_alias="RESPONSE_CACHE_TTL_SECONDS"
    )

    # ==================== Data Governance (trust) ====================
    # Hard routing constraints (opt-in): a violating provider is never used.
    require_no_training: bool = Field(
        default=False, validation_alias="DATA_REQUIRE_NO_TRAINING"
    )
    require_local_only: bool = Field(
        default=False, validation_alias="DATA_REQUIRE_LOCAL_ONLY"
    )
    allowed_regions: str = Field(default="", validation_alias="DATA_ALLOWED_REGIONS")

    # ==================== HTTP Client Timeouts ====================
    http_read_timeout: float = Field(
        default=120.0, validation_alias="HTTP_READ_TIMEOUT"
    )
    http_write_timeout: float = Field(
        default=10.0, validation_alias="HTTP_WRITE_TIMEOUT"
    )
    http_connect_timeout: float = Field(
        default=HTTP_CONNECT_TIMEOUT_DEFAULT,
        validation_alias="HTTP_CONNECT_TIMEOUT",
    )

    # ==================== Fast Prefix Detection ====================
    fast_prefix_detection: bool = True

    # ==================== Optimizations ====================
    enable_network_probe_mock: bool = True
    enable_title_generation_skip: bool = True
    enable_suggestion_mode_skip: bool = True
    enable_filepath_extraction_mock: bool = True

    # ==================== Local web server tools (web_search / web_fetch) ====================
    # Off by default: these tools perform outbound HTTP from the proxy (SSRF risk).
    enable_web_server_tools: bool = Field(
        default=False, validation_alias="ENABLE_WEB_SERVER_TOOLS"
    )
    # Comma-separated URL schemes allowed for web_fetch (default: http,https).
    web_fetch_allowed_schemes: str = Field(
        default="http,https", validation_alias="WEB_FETCH_ALLOWED_SCHEMES"
    )
    # When true, skip private/loopback/link-local IP blocking for web_fetch (lab only).
    web_fetch_allow_private_networks: bool = Field(
        default=False, validation_alias="WEB_FETCH_ALLOW_PRIVATE_NETWORKS"
    )

    # ==================== Debug / diagnostic logging (avoid sensitive content) ====================
    # When false (default), API and SSE helpers log only metadata (counts, lengths, ids).
    log_raw_api_payloads: bool = Field(
        default=False, validation_alias="LOG_RAW_API_PAYLOADS"
    )
    log_raw_sse_events: bool = Field(
        default=False, validation_alias="LOG_RAW_SSE_EVENTS"
    )
    # When false (default), unhandled exceptions log only type + route metadata (no message/traceback).
    log_api_error_tracebacks: bool = Field(
        default=False, validation_alias="LOG_API_ERROR_TRACEBACKS"
    )
    # When false (default), messaging logs omit text/transcription previews (metadata only).
    log_raw_messaging_content: bool = Field(
        default=False, validation_alias="LOG_RAW_MESSAGING_CONTENT"
    )
    # When true, log full Claude CLI stderr, non-JSON lines, and parser error text.
    log_raw_cli_diagnostics: bool = Field(
        default=False, validation_alias="LOG_RAW_CLI_DIAGNOSTICS"
    )
    # When true, log exception text / CLI error strings in messaging (may leak user content).
    log_messaging_error_details: bool = Field(
        default=False, validation_alias="LOG_MESSAGING_ERROR_DETAILS"
    )
    debug_platform_edits: bool = Field(
        default=False, validation_alias="DEBUG_PLATFORM_EDITS"
    )
    debug_subagent_stack: bool = Field(
        default=False, validation_alias="DEBUG_SUBAGENT_STACK"
    )

    # ==================== NIM Settings ====================
    nim: NimSettings = Field(default_factory=NimSettings)

    # ==================== Voice Note Transcription ====================
    voice_note_enabled: bool = Field(
        default=True, validation_alias="VOICE_NOTE_ENABLED"
    )
    # Device: "cpu" | "cuda" | "nvidia_nim"
    # - "cpu"/"cuda": local Whisper (requires voice_local extra: uv sync --extra voice_local)
    # - "nvidia_nim": NVIDIA NIM Whisper API (requires voice extra: uv sync --extra voice)
    whisper_device: str = Field(default="cpu", validation_alias="WHISPER_DEVICE")
    # Whisper model ID or short name (for local Whisper) or NVIDIA NIM model (for nvidia_nim)
    # Local Whisper: "tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"
    # NVIDIA NIM: "nvidia/parakeet-ctc-1.1b-asr", "openai/whisper-large-v3", etc.
    whisper_model: str = Field(default="base", validation_alias="WHISPER_MODEL")
    # Hugging Face token for faster model downloads (optional, for local Whisper)
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")

    # ==================== Bot Wrapper Config ====================
    telegram_bot_token: str | None = None
    allowed_telegram_user_id: str | None = None
    discord_bot_token: str | None = Field(
        default=None, validation_alias="DISCORD_BOT_TOKEN"
    )
    allowed_discord_channels: str | None = Field(
        default=None, validation_alias="ALLOWED_DISCORD_CHANNELS"
    )
    allowed_dir: str = ""
    max_message_log_entries_per_chat: int | None = Field(
        default=None, validation_alias="MAX_MESSAGE_LOG_ENTRIES_PER_CHAT"
    )

    # ==================== Server ====================
    host: str = "0.0.0.0"
    port: int = 8082
    # Optional server API key to protect endpoints (Anthropic-style)
    # Set via env `ANTHROPIC_AUTH_TOKEN`. When empty, no auth is required.
    anthropic_auth_token: str = Field(
        default="", validation_alias="ANTHROPIC_AUTH_TOKEN"
    )

    # Handle empty strings for optional string fields
    @field_validator(
        "telegram_bot_token",
        "allowed_telegram_user_id",
        "discord_bot_token",
        "allowed_discord_channels",
        "model_opus",
        "model_sonnet",
        "model_haiku",
        "enable_opus_thinking",
        "enable_sonnet_thinking",
        "enable_haiku_thinking",
        mode="before",
    )
    @classmethod
    def parse_optional_str(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

    @field_validator("max_message_log_entries_per_chat", mode="before")
    @classmethod
    def parse_optional_log_cap(cls, v: Any) -> Any:
        if v == "" or v is None:
            return None
        return v

    @field_validator("whisper_device")
    @classmethod
    def validate_whisper_device(cls, v: str) -> str:
        if v not in ("cpu", "cuda", "nvidia_nim"):
            raise ValueError(
                f"whisper_device must be 'cpu', 'cuda', or 'nvidia_nim', got {v!r}"
            )
        return v

    @field_validator("messaging_platform")
    @classmethod
    def validate_messaging_platform(cls, v: str) -> str:
        if v not in ("telegram", "discord", "none"):
            raise ValueError(
                f"messaging_platform must be 'telegram', 'discord', or 'none', got {v!r}"
            )
        return v

    @field_validator("messaging_rate_limit")
    @classmethod
    def validate_messaging_rate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("messaging_rate_limit must be > 0")
        return v

    @field_validator("messaging_rate_window")
    @classmethod
    def validate_messaging_rate_window(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("messaging_rate_window must be > 0")
        return float(v)

    @field_validator("web_fetch_allowed_schemes")
    @classmethod
    def validate_web_fetch_allowed_schemes(cls, v: str) -> str:
        schemes = [part.strip().lower() for part in v.split(",") if part.strip()]
        if not schemes:
            raise ValueError("web_fetch_allowed_schemes must list at least one scheme")
        for scheme in schemes:
            if not scheme.isascii() or not scheme.isalpha():
                raise ValueError(
                    f"Invalid URL scheme in web_fetch_allowed_schemes: {scheme!r}"
                )
        return ",".join(schemes)

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, v: str) -> str:
        if v.rstrip("/").endswith("/v1"):
            raise ValueError(
                "OLLAMA_BASE_URL must be the Ollama root URL for native Anthropic "
                "messages, e.g. http://localhost:11434 (without /v1)."
            )
        return v

    @field_validator("model", "model_opus", "model_sonnet", "model_haiku")
    @classmethod
    def validate_model_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if "/" not in v:
            raise ValueError(
                f"Model must be prefixed with provider type. "
                f"Valid providers: {', '.join(SUPPORTED_PROVIDER_IDS)}. "
                f"Format: provider_type/model/name"
            )
        provider = v.split("/", 1)[0]
        if provider not in SUPPORTED_PROVIDER_IDS:
            supported = ", ".join(f"'{p}'" for p in SUPPORTED_PROVIDER_IDS)
            raise ValueError(f"Invalid provider: '{provider}'. Supported: {supported}")
        return v

    @model_validator(mode="after")
    def check_nvidia_nim_api_key(self) -> Settings:
        if (
            self.voice_note_enabled
            and self.whisper_device == "nvidia_nim"
            and not self.nvidia_nim_api_key.strip()
        ):
            raise ValueError(
                "NVIDIA_NIM_API_KEY is required when WHISPER_DEVICE is 'nvidia_nim'. "
                "Set it in your .env file."
            )
        return self

    @model_validator(mode="after")
    def prefer_dotenv_anthropic_auth_token(self) -> Settings:
        """Let explicit .env auth config override stale shell/client tokens."""
        dotenv_value = env_file_override(self.model_config, ANTHROPIC_AUTH_TOKEN_ENV)
        if dotenv_value is not None:
            self.anthropic_auth_token = dotenv_value
        return self

    model_config = SettingsConfigDict(
        env_file=settings_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
