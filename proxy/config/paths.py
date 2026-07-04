"""Shared filesystem paths for Freeway configuration."""

from pathlib import Path

FREEWAY_CONFIG_DIRNAME = ".freeway"
FREEWAY_ENV_FILENAME = ".env"
# Legacy config locations migrated into ~/.freeway/.env on first run.
LEGACY_FCC_CONFIG_DIRNAME = ".fcc"
LEGACY_REPO_DIRNAME = "free-claude-code"
LEGACY_XDG_CONFIG_DIRNAME = ".config"
CLAUDE_WORKSPACE_DIRNAME = "agent_workspace"
FREEWAY_LOGS_DIRNAME = "logs"
SERVER_LOG_FILENAME = "server.log"
CODEX_MODEL_CATALOG_FILENAME = "codex-model-catalog.json"


def config_dir_path() -> Path:
    """Return the default user config directory."""

    return Path.home() / FREEWAY_CONFIG_DIRNAME


def managed_env_path() -> Path:
    """Return the default user-managed env file path."""

    return config_dir_path() / FREEWAY_ENV_FILENAME


def legacy_env_paths() -> tuple[Path, ...]:
    """Return legacy user env paths that can be migrated to ~/.freeway/.env."""

    home = Path.home()
    return (
        home / LEGACY_FCC_CONFIG_DIRNAME / FREEWAY_ENV_FILENAME,
        home / LEGACY_REPO_DIRNAME / FREEWAY_ENV_FILENAME,
        home / LEGACY_XDG_CONFIG_DIRNAME / LEGACY_REPO_DIRNAME / FREEWAY_ENV_FILENAME,
    )


def default_claude_workspace_path() -> Path:
    """Return the default Claude workspace path."""

    return config_dir_path() / CLAUDE_WORKSPACE_DIRNAME


def server_log_path() -> Path:
    """Return the canonical server log path."""

    return config_dir_path() / FREEWAY_LOGS_DIRNAME / SERVER_LOG_FILENAME


def codex_model_catalog_path() -> Path:
    """Return the generated Codex model catalog path."""

    return config_dir_path() / CODEX_MODEL_CATALOG_FILENAME
