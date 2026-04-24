from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.auth import validate_api_key
from mcp_server.services import scheduler_service
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


def _get_scheduler_from_request(request: Request) -> RoutineScheduler:
    scheduler = getattr(request.state, "scheduler", None)
    if isinstance(scheduler, RoutineScheduler):
        return scheduler

    scope_state = request.scope.get("state", {})
    scheduler = scope_state.get("scheduler") if isinstance(scope_state, dict) else None
    if isinstance(scheduler, RoutineScheduler):
        return scheduler

    raise RuntimeError("scheduler not available in request state")


@mcp.custom_route("/api/routines/{name:str}/run", methods=["POST"], include_in_schema=False)
async def run_routine_via_api(request: Request) -> JSONResponse:
    auth_header = request.headers.get("authorization")
    if not validate_api_key(auth_header):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        raw_body = await request.body()
        payload = {} if not raw_body else json.loads(raw_body)
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid json body"}, status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse({"error": "json body must be an object"}, status_code=400)

    task_id = payload.get("task_id")
    if task_id is not None and not isinstance(task_id, str):
        return JSONResponse({"error": "task_id must be a string"}, status_code=400)

    scheduler = _get_scheduler_from_request(request)
    routine_name = request.path_params["name"]
    queued_job_ids = scheduler_service.trigger_routine_now(
        scheduler,
        routine_name,
        task_id=task_id,
    )
    if queued_job_ids is None:
        detail = f"no matching jobs for '{routine_name}'"
        if task_id:
            detail += f" task '{task_id}'"
        return JSONResponse({"error": detail}, status_code=404)

    return JSONResponse(
        {
            "status": "triggered",
            "routine": routine_name,
            "task_id": task_id,
            "queued_job_ids": queued_job_ids,
            "detail": f"triggered {len(queued_job_ids)} task(s)",
        }
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
from .resources import routine_resources  # noqa: E402, F401
