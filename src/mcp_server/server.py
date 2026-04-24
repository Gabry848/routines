from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from scheduler.constants import ROUTINES_PATH
from scheduler.engine import RoutineScheduler
from scheduler.loader import load_jobs



@asynccontextmanager
async def _scheduler_lifespan(server: FastMCP):
    base_path = ROUTINES_PATH
    jobs = load_jobs(base_path)
    scheduler = RoutineScheduler(jobs, base_path=base_path)
    scheduler._scheduler.start()
    scheduler.sync_jobs()
    loop_task = asyncio.create_task(_scheduler_loop(scheduler))
    yield {"scheduler": scheduler}
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    scheduler._scheduler.shutdown()


async def _scheduler_loop(scheduler: RoutineScheduler) -> None:
    try:
        while True:
            await asyncio.sleep(scheduler._reload_interval_seconds)
            scheduler.sync_jobs()
    except asyncio.CancelledError:
        pass


mcp = FastMCP(
    "Scheduler MCP",
    lifespan=_scheduler_lifespan,
)

# Import tools to register them
from .tools import (  # noqa: E402, F401
    routine_tools,
    task_tools,
    scheduler_tools,
    monitoring_tools,
    validation_tools,
    import_export_tools,
)
