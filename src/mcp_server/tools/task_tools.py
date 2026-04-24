from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..services import routine_service, task_service, validation_service
from ..server import mcp


@mcp.tool
def add_task_to_routine(ctx: Context, name: str, task: dict[str, Any]) -> dict[str, Any]:
    """Add a new task to an existing routine's task list in config.json."""
    current = routine_service.get_routine(name)
    if current is None:
        return {"error": f"cannot add task to '{name}' (routine not found or task_id already exists)"}

    existing_tasks = current.config.get("scheduler", {}).get("tasks", [])
    next_index = len(existing_tasks) if isinstance(existing_tasks, list) else 0
    normalized_task = validation_service.normalize_task(
        task,
        routine_name=name,
        default_task_id=f"task-{next_index}",
    )
    existing_ids = {
        existing.get("task_id")
        for existing in existing_tasks
        if isinstance(existing, dict) and isinstance(existing.get("task_id"), str)
    }
    errors = validation_service.validate_task(normalized_task, existing_task_ids=existing_ids)
    if errors:
        return {
            "error": "invalid task payload",
            "validation_errors": errors,
            "normalized_task": normalized_task,
        }

    result = task_service.add_task(name, normalized_task)
    if result is None:
        return {"error": f"cannot add task to '{name}' (routine not found or task_id already exists)"}
    return result


@mcp.tool
def update_task(ctx: Context, name: str, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Modify an existing task by task_id within a routine."""
    current = routine_service.get_routine(name)
    if current is None:
        return {"error": f"task '{task_id}' not found in '{name}'"}

    tasks = current.config.get("scheduler", {}).get("tasks", [])
    if not isinstance(tasks, list):
        return {"error": f"task '{task_id}' not found in '{name}'"}

    existing_task = None
    for task in tasks:
        if isinstance(task, dict) and task.get("task_id") == task_id:
            existing_task = task
            break

    if existing_task is None:
        return {"error": f"task '{task_id}' not found in '{name}'"}

    merged_task = validation_service.normalize_task_update(
        existing_task,
        updates,
        routine_name=name,
        default_task_id=task_id,
    )
    existing_ids = {
        existing.get("task_id")
        for existing in tasks
        if isinstance(existing, dict)
        and isinstance(existing.get("task_id"), str)
        and existing.get("task_id") != task_id
    }
    errors = validation_service.validate_task(merged_task, existing_task_ids=existing_ids)
    if errors:
        return {
            "error": "invalid task update",
            "validation_errors": errors,
            "normalized_task": merged_task,
        }

    result = task_service.replace_task(name, task_id, merged_task)
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
