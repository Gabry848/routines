from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..dependencies import get_scheduler
from ..services import routine_service
from ..server import mcp


@mcp.tool
def list_routines(ctx: Context) -> list[dict[str, Any]]:
    """List all routines discovered by the scheduler with status, tasks, cron, timezone, and next run times."""
    return [r.model_dump() for r in routine_service.list_routines()]


@mcp.tool
def get_routine(ctx: Context, name: str, task_id: str | None = None) -> dict[str, str]:
    """Get full detail of a routine by name. Optionally filter to a specific task by task_id."""
    result = routine_service.get_routine(name, task_id=task_id)
    if result is None:
        return {"error": f"routine '{name}' not found"}
    return result.model_dump()


@mcp.tool
def add_routine(ctx: Context, name: str, config: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Create a new routine with directory, config.json, prompt file, and env directory."""
    result = routine_service.create_routine(name, config, prompt)
    if result is None:
        return {"error": f"routine '{name}' already exists"}
    return result.model_dump()


@mcp.tool
def update_routine_config(ctx: Context, name: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Safely modify routine config fields. Accepts partial updates deep-merged into existing config."""
    result = routine_service.update_routine_config(name, updates)
    if result is None:
        return {"error": f"routine '{name}' not found"}
    return result


@mcp.tool
def delete_routine(ctx: Context, name: str, mode: str = "disable") -> dict[str, str]:
    """Delete a routine. Mode 'disable' sets enabled=false, 'delete' removes files."""
    success = routine_service.delete_routine(name, mode=mode)
    if not success:
        return {"error": f"routine '{name}' not found"}
    return {"status": "ok", "mode": mode}


@mcp.tool
def rename_routine(ctx: Context, name: str, new_name: str) -> dict[str, Any]:
    """Rename a routine directory, maintaining coherence between directory name and config."""
    result = routine_service.rename_routine(name, new_name)
    if result is None:
        return {"error": f"cannot rename '{name}' to '{new_name}' (source missing or target exists)"}
    return result.model_dump()


@mcp.tool
def clone_routine(ctx: Context, name: str, new_name: str) -> dict[str, Any]:
    """Duplicate an existing routine with new name and regenerated task IDs."""
    result = routine_service.clone_routine(name, new_name)
    if result is None:
        return {"error": f"cannot clone '{name}' to '{new_name}'"}
    return result.model_dump()


@mcp.tool
def enable_routine(ctx: Context, name: str) -> dict[str, str]:
    """Enable a routine by setting scheduler.enabled to true."""
    success = routine_service.set_routine_enabled(name, True)
    if not success:
        return {"error": f"routine '{name}' not found"}
    return {"status": "enabled", "routine": name}


@mcp.tool
def disable_routine(ctx: Context, name: str) -> dict[str, str]:
    """Disable a routine by setting scheduler.enabled to false."""
    success = routine_service.set_routine_enabled(name, False)
    if not success:
        return {"error": f"routine '{name}' not found"}
    return {"status": "disabled", "routine": name}
