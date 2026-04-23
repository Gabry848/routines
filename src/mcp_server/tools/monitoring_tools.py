from __future__ import annotations

from fastmcp import Context

from ..dependencies import get_scheduler
from ..services import scheduler_service, log_service
from ..server import mcp


@mcp.tool
def get_execution_logs(ctx: Context, name: str, limit: int = 5) -> list[dict]:
    """Read the last N log files for a routine from its logs directory."""
    return log_service.get_logs(name, limit=limit)


@mcp.tool
def list_execution_history(ctx: Context, name: str | None = None, limit: int = 20) -> list[dict]:
    """List execution history with outcome, duration, and timestamps. Filter by routine name."""
    scheduler = get_scheduler(ctx)
    return [e.model_dump() for e in scheduler_service.get_execution_history(scheduler, name=name, limit=limit)]


@mcp.tool
def get_last_error(ctx: Context, name: str) -> dict[str, str]:
    """Get the most recent error for a routine — parsing, scheduling, or runtime."""
    scheduler = get_scheduler(ctx)
    error = scheduler._last_errors.get(name)
    if error is None:
        return {"status": "no errors found", "routine": name}
    return {
        "routine_name": error.routine_name,
        "task_id": error.task_id,
        "error_type": error.error_type,
        "message": error.message,
        "timestamp": error.timestamp.isoformat(),
    }
