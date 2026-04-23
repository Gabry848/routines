## Context

The scheduler runs as a single async Python process using APScheduler. It discovers routines from `routines/` dir, loads `config.json` per routine, executes tasks on cron schedules via `claude_agent_sdk`. The `RoutineScheduler` engine holds all live state: scheduled jobs, signatures, reload interval. Currently no execution tracking, no heartbeat, no task-level enable/disable.

## Goals / Non-Goals

**Goals:**
- Expose scheduler management as real MCP tools via FastMCP
- Claude Code / Codex connects via Streamable HTTP transport
- API key auth via `SCHEDULER_MCP_API_KEY` env var
- Direct access to scheduler state (same process)
- Filesystem as source of truth

**Non-Goals:**
- REST API (this is MCP protocol, not HTTP endpoints)
- Multi-user auth / RBAC
- Cooperative cancellation of running routines (deferred — needs `Routine.start()` refactor with cancel tokens)
- SSE change streaming (deferred)
- Persistent database

## Decisions

### FastMCP with `@mcp.tool` decorators
FastMCP auto-generates JSON schemas from Python type hints and docstrings. Claude Code discovers tools via MCP protocol. No manual schema definition needed.

```python
from fastmcp import FastMCP

mcp = FastMCP("Scheduler MCP")

@mcp.tool
def list_routines() -> list[dict]:
    """List all routines with status, cron, timezone, next run."""
    ...
```

**Alternative:** Raw MCP SDK — more boilerplate, manual schema management. Rejected.

### Streamable HTTP transport
`mcp.run(transport="streamable-http", host="0.0.0.0", port=8080, path="/mcp")` — recommended transport for production (FastMCP 2.3+). Claude Code connects via URL.

**Alternative:** stdio — requires starting server as subprocess, no remote access. Rejected because user wants HTTP with API key.

**Alternative:** SSE — legacy, replaced by Streamable HTTP.

### Same-process architecture
MCP server runs **inside** the scheduler process. The scheduler's `app.py` starts both the APScheduler loop and the FastMCP HTTP server. MCP tools access `RoutineScheduler` instance directly via shared reference.

```
app.py
├── RoutineScheduler (APScheduler loop)
└── FastMCP HTTP server (streamable-http on :8080/mcp)
    └── Tools access scheduler._jobs, scheduler.sync_jobs(), etc.
```

How: FastMCP lifespan handler receives the `RoutineScheduler` instance. Tools read it from the lifespan state. Scheduler loop runs in background asyncio task.

```python
@asynccontextmanager
async def app_lifecycle(server: FastMCP):
    scheduler = RoutineScheduler(...)
    scheduler._scheduler.start()
    scheduler.sync_jobs()
    task = asyncio.create_task(_scheduler_loop(scheduler))
    yield {"scheduler": scheduler}
    task.cancel()
    scheduler._scheduler.shutdown()
```

**Alternative:** Separate process — requires IPC, can't access live state. Rejected for Phase 1.

### API Key Auth
FastMCP supports custom auth via middleware. Read `SCHEDULER_MCP_API_KEY` env var. Validate `Authorization: Bearer <key>` header on every request. If env var is empty/missing, auth is disabled (dev mode).

### File system as source of truth
All write tools modify `routines/<name>/config.json` on disk. Scheduler's existing `sync_jobs()` picks up changes on next poll (or forced via `reload_routines` tool).

## Risks / Trade-offs

- **Same-process coupling**: MCP server crash takes down scheduler. → Mitigation: FastMCP/uvicorn is battle-tested; keep tool logic thin (delegate to service layer).
- **No cooperative cancellation**: `Routine.start()` is a long-running async call with no cancel mechanism. → Deferred to Phase 2. `cancel_running_routine` tool returns "not supported" for now.
- **task.enabled not in loader**: `load_jobs()` must be updated to check `task.get("enabled", True)` before creating Routine instances. Without this, disabled tasks would still be scheduled.
- **Streamable HTTP maturity**: Relatively new transport (FastMCP 2.3). → Mitigation: SSE fallback available if issues arise.
