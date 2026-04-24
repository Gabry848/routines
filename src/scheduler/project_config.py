import json
from pathlib import Path
from typing import Any

from .constants import (
    LOCAL_CLAUDE_JSON_PATH,
    LOCAL_CLAUDE_SETTINGS_PATH,
    LOCAL_CONFIG_PATH,
)


HOME_CLAUDE_JSON_PATH = Path.home() / ".claude.json"
HOME_CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

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


def _project_scope_chain(project_root: Path | None) -> list[Path]:
    if project_root is None:
        return []

    resolved = project_root.resolve()
    chain: list[Path] = []
    current = resolved
    while True:
        chain.append(current)
        if current.parent == current:
            break
        current = current.parent
    chain.reverse()
    return chain


def _extract_project_settings(data: dict[str, Any], project_root: Path | None) -> dict[str, Any]:
    projects = data.get("projects")
    if not isinstance(projects, dict):
        return {}

    merged: dict[str, Any] = {}
    for candidate in _project_scope_chain(project_root):
        scoped = projects.get(str(candidate))
        if isinstance(scoped, dict):
            merged.update(scoped)
    return merged


def _load_home_claude_settings() -> dict[str, Any]:
    return _load_json_dict(HOME_CLAUDE_SETTINGS_PATH)


def _load_home_claude_json() -> dict[str, Any]:
    return _load_json_dict(HOME_CLAUDE_JSON_PATH)


def build_runtime_settings(project_root: Path | None = None) -> dict[str, Any]:
    runtime_settings: dict[str, Any] = {}

    home_settings = _load_home_claude_settings()
    source_data = dict(home_settings)
    source_data.update(load_local_claude_settings())

    source_env = source_data.get("env", {})
    if isinstance(source_env, dict):
        filtered_env = {
            key: value
            for key, value in source_env.items()
            if key in DOCKER_SETTINGS_ENV_KEYS and isinstance(value, str) and value
        }
        if filtered_env:
            runtime_settings["env"] = filtered_env

    for key in ("enabledPlugins", "extraKnownMarketplaces", "permissions"):
        value = source_data.get(key)
        if isinstance(value, dict) and value:
            runtime_settings[key] = value

    discovered_mcp = discover_local_mcp_servers(project_root=project_root)
    if discovered_mcp:
        runtime_settings["mcpServers"] = discovered_mcp

    return runtime_settings


def discover_local_mcp_servers(project_root: Path | None = None) -> dict[str, dict[str, Any]]:
    servers: dict[str, dict[str, Any]] = {}

    home_claude_json = _load_home_claude_json()
    home_claude_settings = _load_home_claude_settings()

    data_sources = (
        home_claude_settings,
        _extract_project_settings(home_claude_json, project_root),
        home_claude_json,
        load_local_claude_json(),
        load_local_claude_settings(),
    )

    for data in data_sources:
        mcp = data.get("mcpServers", {})
        if isinstance(mcp, dict):
            servers.update(mcp)

    return servers
