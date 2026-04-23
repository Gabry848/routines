from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..services import routine_service
from ..server import mcp


@mcp.tool
def export_routine(ctx: Context, name: str) -> dict:
    """Export a complete routine as JSON with config, prompt text, and file listing."""
    result = routine_service.export_routine(name)
    if result is None:
        return {"error": f"routine '{name}' not found"}
    return result.model_dump()


@mcp.tool
def import_routine(ctx: Context, name: str, config: dict[str, Any], prompt: str) -> dict:
    """Import a routine from JSON payload — creates directory, config.json, and prompt file."""
    result = routine_service.import_routine(name, config, prompt)
    if result is None:
        return {"error": f"routine '{name}' already exists"}
    return result.model_dump()
