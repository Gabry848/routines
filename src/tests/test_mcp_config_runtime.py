import json
from pathlib import Path

from scheduler.project_config import build_runtime_settings, discover_local_mcp_servers
from scheduler.routine import RoutineConfig


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_discover_local_mcp_servers_falls_back_to_home_project_config(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir()

    home_claude_json = tmp_path / "home" / ".claude.json"
    home_claude_settings = tmp_path / "home" / ".claude" / "settings.json"
    local_claude_json = project_root / ".config" / "routines" / "claude.json"
    local_settings = project_root / ".config" / "routines" / "claude" / "settings.json"

    _write_json(
        home_claude_json,
        {
            "projects": {
                str(project_root): {
                    "mcpServers": {
                        "memory": {
                            "type": "stdio",
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-memory"],
                        }
                    }
                }
            }
        },
    )
    _write_json(home_claude_settings, {})
    _write_json(local_claude_json, {})
    _write_json(local_settings, {})

    monkeypatch.setattr("scheduler.project_config.HOME_CLAUDE_JSON_PATH", home_claude_json)
    monkeypatch.setattr("scheduler.project_config.HOME_CLAUDE_SETTINGS_PATH", home_claude_settings)
    monkeypatch.setattr("scheduler.project_config.LOCAL_CLAUDE_JSON_PATH", local_claude_json)
    monkeypatch.setattr("scheduler.project_config.LOCAL_CLAUDE_SETTINGS_PATH", local_settings)

    servers = discover_local_mcp_servers(project_root=project_root)

    assert "memory" in servers
    assert servers["memory"]["command"] == "npx"


def test_build_runtime_settings_keeps_permissions_and_project_mcp(monkeypatch, tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir()

    home_claude_json = tmp_path / "home" / ".claude.json"
    home_claude_settings = tmp_path / "home" / ".claude" / "settings.json"
    local_claude_json = project_root / ".config" / "routines" / "claude.json"
    local_settings = project_root / ".config" / "routines" / "claude" / "settings.json"

    _write_json(
        home_claude_json,
        {
            "projects": {
                str(project_root): {
                    "mcpServers": {
                        "memory": {
                            "type": "stdio",
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-memory"],
                        }
                    }
                }
            }
        },
    )
    _write_json(
        home_claude_settings,
        {
            "env": {"ANTHROPIC_AUTH_TOKEN": "token", "IGNORED": "nope"},
            "permissions": {"mcp__memory__read_graph": {"mode": "auto"}},
        },
    )
    _write_json(local_claude_json, {})
    _write_json(local_settings, {})

    monkeypatch.setattr("scheduler.project_config.HOME_CLAUDE_JSON_PATH", home_claude_json)
    monkeypatch.setattr("scheduler.project_config.HOME_CLAUDE_SETTINGS_PATH", home_claude_settings)
    monkeypatch.setattr("scheduler.project_config.LOCAL_CLAUDE_JSON_PATH", local_claude_json)
    monkeypatch.setattr("scheduler.project_config.LOCAL_CLAUDE_SETTINGS_PATH", local_settings)

    settings = build_runtime_settings(project_root=project_root)

    assert settings["env"] == {"ANTHROPIC_AUTH_TOKEN": "token"}
    assert "permissions" in settings
    assert "memory" in settings["mcpServers"]


def test_build_agent_options_allows_all_tools_for_selected_mcp_server(monkeypatch):
    monkeypatch.setattr(
        "scheduler.routine.resolve_server_names",
        lambda server_names, project_root=None: {
            name: {"type": "stdio", "command": "npx"} for name in server_names
        },
    )

    config = RoutineConfig("Ciao")
    config.model_config = {
        "model": "haiku",
        "allowed_tools": ["Read"],
        "mcp_servers": ["memory"],
        "mcp_selected_tools": {},
        "sandbox": True,
    }

    options = config.build_agent_options(Path("/tmp"))

    assert "Read" in options.allowed_tools
    assert "mcp__memory__" in options.allowed_tools
    assert options.permission_mode == "bypassPermissions"
    assert options.extra_args["allow-dangerously-skip-permissions"] is None


def test_merge_auto_permissions_adds_missing_mcp_permissions():
    settings_data = {
        "permissions": {
            "Read": {"prompt": "read files", "mode": "auto"},
        }
    }

    RoutineConfig._merge_auto_permissions(
        settings_data,
        ["Read", "mcp__memory__", "mcp__memory__read_graph"],
    )

    assert settings_data["permissions"]["Read"]["prompt"] == "read files"
    assert settings_data["permissions"]["mcp__memory__"]["mode"] == "auto"
    assert settings_data["permissions"]["mcp__memory__read_graph"]["mode"] == "auto"
