import json
from pathlib import Path
from typing import Any


def discover_mcp_servers(
    project_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    home = Path.home()
    servers: dict[str, dict[str, Any]] = {}

    sources = [
        home / ".claude.json",
        home / ".claude" / "settings.json",
    ]

    if project_root:
        sources.append(project_root / ".claude" / "settings.json")
        sources.append(project_root / ".mcp.json")

    for path in sources:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue
            mcp = data.get("mcpServers", {})
            if isinstance(mcp, dict):
                servers.update(mcp)
        except (json.JSONDecodeError, OSError):
            continue

    return servers


def resolve_server_names(
    server_names: list[str],
    project_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    available = discover_mcp_servers(project_root=project_root)
    missing = [name for name in server_names if name not in available]
    if missing:
        raise ValueError(
            f"MCP servers not found: {', '.join(missing)}. "
            f"Available: {', '.join(sorted(available)) or '(none)'}"
        )
    return {name: available[name] for name in server_names}


def get_available_server_names(
    project_root: Path | None = None,
) -> list[str]:
    return sorted(discover_mcp_servers(project_root=project_root).keys())
