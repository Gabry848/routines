from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from scheduler.engine import RoutineScheduler


def get_scheduler(ctx: Context) -> RoutineScheduler:
    return ctx.request_context.lifespan_state["scheduler"]
