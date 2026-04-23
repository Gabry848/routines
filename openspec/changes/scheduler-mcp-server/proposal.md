## Why

The scheduler has no control plane. Operators manage routines by editing files on disk and waiting for the 10-second polling sync. A real MCP server exposes scheduler management as tools that Claude Code and Codex can call directly, enabling conversational routine management.

## What Changes

- New MCP server in `src/mcp_server/` using **FastMCP** (`@mcp.tool` decorators, auto-generated schemas)
- **Streamable HTTP** transport (`mcp.run(transport="streamable-http")`) with API key auth via `SCHEDULER_MCP_API_KEY` env var
- Runs in the **same process** as the scheduler — direct access to `RoutineScheduler` state
- Runtime primitives added to `engine.py`: execution tracking dict, heartbeat timestamp, last sync timestamp
- Runtime primitive added to `loader.py`: `task.enabled` filter
- Phase 1 tools: routine CRUD, task CRUD, scheduler control, validation, import/export
- **Deferred**: `cancel_running_routine` (needs cooperative cancellation in `Routine.start()`), `watch_routine_changes` (SSE streaming)

## Capabilities

### New Capabilities
- `mcp-tools`: All MCP tools exposed via FastMCP — routine CRUD, task CRUD, scheduler control, validation, import/export, schedule preview
- `runtime-primitives`: Execution tracking, heartbeat, task.enabled filter — foundation for MCP tools to read live scheduler state

### Modified Capabilities

## Impact

- New package `src/mcp_server/` with FastMCP
- New dependencies: `fastmcp` (pulls in `mcp`, `uvicorn`, `starlette`)
- `src/scheduler/engine.py`: added execution tracking, heartbeat
- `src/scheduler/loader.py`: added `task.enabled` filter
- `src/scheduler/app.py`: starts MCP server alongside scheduler
- `src/pyproject.toml`: new dep + entry point
- No breaking changes to existing scheduler
