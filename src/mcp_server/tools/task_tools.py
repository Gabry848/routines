from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..services import task_service
from ..server import mcp


@mcp.tool
def add_task_to_routine(ctx: Context, name: str, task: dict[str, Any]) -> dict[str, Any]:
    """Add a new task to an existing routine's task list in config.json."""
    result = task_service.add_task(name, task)
    if result is None:
        return {"error": f"cannot add task to '{name}' (routine not found or task_id already exists)"}
    return result


@mcp.tool
def update_task(ctx: Context, name: str, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Modify an existing task by task_id within a routine."""
    result = task_service.update_task(name, task_id, updates)
    if result is None:
        return {"error": f"task '{task_id}' not found in '{name}'"}
    return result


@mcp.tool
def delete_task(ctx: Context, name: str, task_id: str) -> dict[str, str]:
    """Remove a specific task from a routine's task list by task_id."""
    success = task_service.delete_task(name, task_id)
    if not success:
        return {"error": f"task '{task_id}' not found in '{name}'"}
    return {"status": "deleted", "routine": name, "task_id": task_id}


@mcp.tool
def enable_task(ctx: Context, name: str, task_id: str) -> dict[str, str]:
    """Enable a task by setting task.enabled to true."""
    success = task_service.set_task_enabled(name, task_id, True)
    if not success:
        return {"error": f"task '{task_id}' not found in '{name}'"}
    return {"status": "enabled", "routine": name, "task_id": task_id}


@mcp.tool
def disable_task(ctx: Context, name: str, task_id: str) -> dict[str, str]:
    """Disable a task by setting task.enabled to false."""
    success = task_service.set_task_enabled(name, task_id, False)
    if not success:
        return {"error": f"task '{task_id}' not found in '{name}'"}
    return {"status": "disabled", "routine": name, "task_id": task_id}
