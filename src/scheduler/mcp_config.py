from typing import Any
from pathlib import Path

from .project_config import discover_local_mcp_servers

def discover_mcp_servers(
    project_root: object | None = None,
) -> dict[str, dict[str, Any]]:
    return discover_local_mcp_servers()


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
