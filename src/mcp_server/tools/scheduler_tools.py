from __future__ import annotations

from fastmcp import Context

from ..dependencies import get_scheduler
from ..services import scheduler_service
from ..server import mcp


@mcp.tool
def reload_routines(ctx: Context) -> dict[str, int]:
    """Force immediate synchronization with the filesystem, bypassing the polling interval."""
    scheduler = get_scheduler(ctx)
    added, updated, removed = scheduler_service.reload_routines(scheduler)
    return {"added": added, "updated": updated, "removed": removed}


@mcp.tool
def run_routine_now(ctx: Context, name: str, task_id: str | None = None) -> dict[str, str]:
    """Execute a routine immediately, bypassing the cron schedule. Optionally target a specific task."""
    scheduler = get_scheduler(ctx)
    result = scheduler_service.run_routine_now(scheduler, name, task_id=task_id)
    if result is None:
        return {"error": f"no matching jobs for '{name}'" + (f" task '{task_id}'" if task_id else "")}
    return {"status": "triggered", "detail": result}


@mcp.tool
def get_scheduler_status(ctx: Context) -> dict:
    """Get global scheduler state: status, heartbeat, polling interval, active jobs, routine counts."""
    scheduler = get_scheduler(ctx)
    return scheduler_service.get_status(scheduler).model_dump()


@mcp.tool
def list_running_executions(ctx: Context) -> list[dict]:
    """List all routines currently in execution with start time, routine name, and task_id."""
    scheduler = get_scheduler(ctx)
    return [e.model_dump() for e in scheduler_service.list_running_executions(scheduler)]


@mcp.tool
def check_filesystem_drift(ctx: Context) -> dict:
    """Compare on-disk state with in-memory scheduler state without applying changes."""
    scheduler = get_scheduler(ctx)
    return scheduler_service.check_filesystem_drift(scheduler).model_dump()
