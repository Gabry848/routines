# Routines Project

Automated scheduler that runs Claude agent routines on cron schedules, with an MCP server for remote management via Claude Code / Codex.

## Structure

- `routines/` — routine definitions (each subfolder = one routine)
- `src/scheduler/` — Python scheduler engine using `claude_agent_sdk`
- `src/scheduler/constants.py` — `ROUTINES_PATH` points to `routines/`
- `src/mcp_server/` — FastMCP server exposing scheduler management tools (30 tools)

## Routine anatomy

Each routine folder (`routines/<name>/`) contains:
- `config.json` — scheduler config + model config (see `src/scheduler/loader.py`, `src/scheduler/routine.py`)
- `PROMT.md` (or `PROMPT.md`, `prompt.md`, `promt.md`) — prompt sent to Claude
- `env/` — agent working directory (`cwd`)
- `logs/` — auto-created execution logs
- `setup.sh` — optional pre-execution script

## config.json schema

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "task_id": "my-task",
        "job_name": "display-name",
        "enabled": true,
        "schedule": { "type": "cron", "expression": "0 9 * * *" },
        "startup_script": "setup.sh"
      }
    ]
  },
  "model_config": { "model": "sonnet", "allowed_tools": ["Bash", "Read", "Edit"] },
  "docker": { "enabled": false },
  "environment": { "isolated_runs": false, "keep_executions": false }
}
```

- `task.enabled` — if `false`, loader skips the task (defaults to `true`)
- `scheduler.enabled` — if `false`, entire routine is skipped

## Creating routines

Use the `/new-routine` skill or follow the pattern in existing routines (e.g. `notion-backlog-report`).

## Running

### Scheduler + MCP server (recommended)
```bash
cd src && uv run mcp-server
```
Starts scheduler + MCP on `http://0.0.0.0:8080/mcp`. One process, both services.

### Scheduler only (legacy)
```bash
cd src && uv run python -c "from scheduler.app import run_scheduler; run_scheduler()"
```

### MCP auth
Set `SCHEDULER_MCP_API_KEY` env var to require `Authorization: Bearer <key>` header. If unset, auth is disabled.

## MCP server architecture

FastMCP server runs in the same process as the scheduler. Tools access `RoutineScheduler` state directly via lifespan context.

- `src/mcp_server/server.py` — FastMCP instance, lifespan starts scheduler loop in background asyncio task
- `src/mcp_server/auth.py` — API key validation from `SCHEDULER_MCP_API_KEY` env var
- `src/mcp_server/models.py` — Pydantic models for routine/task/execution data
- `src/mcp_server/dependencies.py` — helper to get scheduler from MCP context
- `src/mcp_server/services/` — business logic layer (routine_service, task_service, scheduler_service, validation_service, log_service)
- `src/mcp_server/tools/` — `@mcp.tool` decorated functions registered on the FastMCP instance

### MCP tools (30)

**Routine CRUD:** `list_routines`, `get_routine`, `add_routine`, `update_routine_config`, `delete_routine`, `rename_routine`, `clone_routine`, `enable_routine`, `disable_routine`, `export_routine`, `import_routine`

**Task CRUD:** `add_task_to_routine`, `update_task`, `delete_task`, `enable_task`, `disable_task`

**Scheduler control:** `reload_routines`, `run_routine_now`, `get_scheduler_status`, `list_running_executions`, `check_filesystem_drift`

**Monitoring:** `get_execution_logs`, `list_execution_history`, `get_last_error`

**Validation/testing:** `validate_routine_config`, `preview_schedule`, `test_startup_script`, `test_prompt`, `list_available_models_tools_plugins`, `suggest_task_id`

## Key code paths

- Discovery: `src/scheduler/loader.py:discover_routines()` scans `routines/` for subdirs
- Config loading: `src/scheduler/loader.py:load_jobs()` reads `config.json` per routine, filters `task.enabled`
- Scheduling: `src/scheduler/engine.py:RoutineScheduler.sync_jobs()` syncs filesystem → APScheduler jobs
- Execution: `src/scheduler/engine.py:RoutineScheduler._run_tracked_job()` wraps `Routine.start()` with tracking
- Execution tracking: `engine._running_executions` (live), `engine._execution_history` (records), `engine._last_errors` (per-routine)
- Agent: `src/scheduler/agent.py:ClaudeAgent.run()` streams Claude output and writes logs
