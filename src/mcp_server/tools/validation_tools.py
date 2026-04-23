from __future__ import annotations

from typing import Any

from fastmcp import Context

from ..services import validation_service
from ..server import mcp


@mcp.tool
def validate_routine_config(ctx: Context, config: dict[str, Any]) -> dict:
    """Validate a routine config for schema correctness, cron expression, timezone, and references."""
    return validation_service.validate_config(config).model_dump()


@mcp.tool
def preview_schedule(ctx: Context, name: str | None = None, cron: str | None = None, timezone: str = "UTC", count: int = 5) -> list[str] | dict:
    """Preview the next N run times for a routine or a raw cron expression."""
    if cron:
        return validation_service.preview_schedule(cron, timezone=timezone, count=count)
    if name:
        from ..services.routine_service import _load_config, _build_task_summaries
        config = _load_config(name)
        if config is None:
            return {"error": f"routine '{name}' not found"}
        tasks = _build_task_summaries(config)
        results = {}
        for t in tasks:
            if t.cron:
                results[t.task_id] = validation_service.preview_schedule(t.cron, timezone=t.timezone, count=count)
        return results
    return {"error": "provide either 'name' or 'cron' parameter"}


@mcp.tool
def test_startup_script(ctx: Context, name: str) -> dict:
    """Run a routine's startup_script in a controlled subprocess and return output, exit code, and duration."""
    result = validation_service.test_startup_script(name)
    if isinstance(result, str):
        return {"error": result}
    return result.model_dump()


@mcp.tool
def test_prompt(ctx: Context, name: str) -> dict:
    """Validate a routine's prompt file — check existence, length, and content."""
    return validation_service.test_prompt(name).model_dump()


@mcp.tool
def list_available_models_tools_plugins(ctx: Context) -> dict[str, list[str]]:
    """List the available models, tools, and plugins that can be used in model_config."""
    return validation_service.list_available_options()


@mcp.tool
def suggest_task_id(ctx: Context, name: str) -> dict[str, str]:
    """Generate a unique task_id that avoids collisions with existing tasks in a routine."""
    task_id = validation_service.suggest_task_id(name)
    return {"task_id": task_id, "routine": name}
