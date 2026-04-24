from pathlib import Path

from .constants import ROUTINES_PATH
from .engine import RoutineScheduler
from .loader import load_jobs


def run_scheduler(base_path: Path = ROUTINES_PATH) -> None:
    """Run the scheduler without the MCP server (legacy mode)."""
    import asyncio
    jobs = load_jobs(base_path)
    scheduler = RoutineScheduler(jobs, base_path=base_path)
    asyncio.run(scheduler.run_forever())


def run_scheduler_with_mcp(
    base_path: Path = ROUTINES_PATH,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    """Run the scheduler with the MCP server (HTTP streamable transport)."""
    from mcp_server.server import mcp
    mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
