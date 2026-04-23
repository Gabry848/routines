import json
from pathlib import Path
from typing import Any

from .constants import (
    LOCAL_CLAUDE_JSON_PATH,
    LOCAL_CLAUDE_SETTINGS_PATH,
    LOCAL_CONFIG_PATH,
)


DOCKER_SETTINGS_ENV_KEYS = {
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "API_TIMEOUT_MS",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
}


def ensure_local_config_dirs() -> None:
    LOCAL_CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    LOCAL_CLAUDE_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOCAL_CLAUDE_SETTINGS_PATH.exists():
        with LOCAL_CLAUDE_SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
            f.write("\n")
    if not LOCAL_CLAUDE_JSON_PATH.exists():
        with LOCAL_CLAUDE_JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
            f.write("\n")


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def load_local_claude_settings() -> dict[str, Any]:
    return _load_json_dict(LOCAL_CLAUDE_SETTINGS_PATH)


def load_local_claude_json() -> dict[str, Any]:
    return _load_json_dict(LOCAL_CLAUDE_JSON_PATH)


def save_local_claude_settings(data: dict[str, Any]) -> None:
    ensure_local_config_dirs()
    with LOCAL_CLAUDE_SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def save_local_claude_json(data: dict[str, Any]) -> None:
    ensure_local_config_dirs()
    with LOCAL_CLAUDE_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def build_runtime_settings() -> dict[str, Any]:
    source_data = load_local_claude_settings()
    if not source_data:
        return {}

    runtime_settings: dict[str, Any] = {}

    source_env = source_data.get("env", {})
    if isinstance(source_env, dict):
        filtered_env = {
            key: value
            for key, value in source_env.items()
            if key in DOCKER_SETTINGS_ENV_KEYS and isinstance(value, str) and value
        }
        if filtered_env:
            runtime_settings["env"] = filtered_env

    for key in ("enabledPlugins", "extraKnownMarketplaces", "mcpServers"):
        value = source_data.get(key)
        if isinstance(value, dict) and value:
            runtime_settings[key] = value

    return runtime_settings


def discover_local_mcp_servers() -> dict[str, dict[str, Any]]:
    servers: dict[str, dict[str, Any]] = {}

    for data in (load_local_claude_json(), load_local_claude_settings()):
        mcp = data.get("mcpServers", {})
        if isinstance(mcp, dict):
            servers.update(mcp)

    return servers
