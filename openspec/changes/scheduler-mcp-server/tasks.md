## 1. Runtime Primitives

- [x] 1.1 Add `task.enabled` filter to `load_jobs()` in `src/scheduler/loader.py` — skip tasks where `enabled: false`, default to `True`
- [x] 1.2 Add execution tracking dict to `RoutineScheduler` in `src/scheduler/engine.py` — `_running_executions: dict[str, ExecutionRecord]` with `started_at`, `routine_name`, `task_id`
- [x] 1.3 Add heartbeat fields to `RoutineScheduler` — `started_at: datetime`, `last_sync_at: datetime`, update on `sync_jobs()` and init
- [x] 1.4 Add execution history list to `RoutineScheduler` — `_execution_history: list[ExecutionRecord]` with `status`, `started_at`, `finished_at`
- [x] 1.5 Add error tracking list to `RoutineScheduler` — `_last_errors: dict[str, ErrorRecord]` keyed by routine name
- [x] 1.6 Wrap `Routine.start()` in engine to register/deregister executions and record outcomes in history/errors

## 2. Project Setup

- [x] 2.1 Add `fastmcp` dependency to `src/pyproject.toml`
- [x] 2.2 Create `src/mcp_server/__init__.py`
- [x] 2.3 Create `src/mcp_server/server.py` — FastMCP instance with lifespan handler that receives `RoutineScheduler`, starts scheduler loop in background task
- [x] 2.4 Create `src/mcp_server/auth.py` — API key validation reading `SCHEDULER_MCP_API_KEY` env var from `Authorization: Bearer` header
- [x] 2.5 Create `src/mcp_server/models.py` — Pydantic models for routine/task/config/validation/execution data

## 3. Service Layer

- [x] 3.1 Create `src/mcp_server/services/routine_service.py` — filesystem CRUD for routines (discover, get, create, update config, delete, rename, clone, export, import)
- [x] 3.2 Create `src/mcp_server/services/task_service.py` — task-level operations within routines (add, update, delete, enable/disable)
- [x] 3.3 Create `src/mcp_server/services/scheduler_service.py` — scheduler interaction (reload, run now, status, heartbeat, execution tracking)
- [x] 3.4 Create `src/mcp_server/services/validation_service.py` — config validation, cron preview, task ID suggestion, prompt validation
- [x] 3.5 Create `src/mcp_server/services/log_service.py` — read log files from `routines/<name>/logs/`

## 4. MCP Tools

- [x] 4.1 Create `src/mcp_server/tools/routine_tools.py` — `list_routines`, `get_routine`, `add_routine`, `update_routine_config`, `delete_routine`, `rename_routine`, `clone_routine`, `enable_routine`, `disable_routine`
- [x] 4.2 Create `src/mcp_server/tools/task_tools.py` — `add_task_to_routine`, `update_task`, `delete_task`, `enable_task`, `disable_task`
- [x] 4.3 Create `src/mcp_server/tools/scheduler_tools.py` — `reload_routines`, `run_routine_now`, `get_scheduler_status`, `list_running_executions`, `check_filesystem_drift`
- [x] 4.4 Create `src/mcp_server/tools/monitoring_tools.py` — `get_execution_logs`, `list_execution_history`, `get_last_error`
- [x] 4.5 Create `src/mcp_server/tools/validation_tools.py` — `validate_routine_config`, `preview_schedule`, `test_startup_script`, `test_prompt`, `list_available_models_tools_plugins`, `suggest_task_id`
- [x] 4.6 Create `src/mcp_server/tools/import_export_tools.py` — `export_routine`, `import_routine`
- [x] 4.7 Register all tool modules in `src/mcp_server/server.py`

## 5. Integration

- [x] 5.1 Modify `src/scheduler/app.py` — start FastMCP server alongside scheduler using `mcp.run(transport="streamable-http", ...)`
- [x] 5.2 Add `mcp-server` entry point to `src/pyproject.toml`
- [x] 5.3 Create `src/mcp_server/dependencies.py` — helper to access scheduler instance from lifespan state in tool functions

## 6. Testing

- [x] 6.1 Create `src/tests/test_runtime_primitives.py` — test task.enabled filter, execution tracking, heartbeat, history, errors
- [x] 6.2 Create `src/tests/test_mcp_tools.py` — test MCP tool functions with mock scheduler
- [x] 6.3 Create `src/tests/test_routine_service.py` — test filesystem CRUD operations
- [x] 6.4 Create `src/tests/test_validation_service.py` — test config validation, cron preview
