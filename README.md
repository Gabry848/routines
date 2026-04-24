# Routines

![Routines](./resources/copertina.png)

Run AI agents on a schedule, not by hand.

Routines is a scheduler for Claude Code / Codex agents that lets you define recurring jobs, isolate their runtime, and manage everything through an MCP server. Instead of reopening the same workflow every morning, every week, or after every event, you define it once and let it run.

## What You Get

- Scheduled AI work: run agents on cron schedules.
- Repeatable execution: each routine has a prompt, config, optional setup script, and working directory.
- Safer runtime boundaries: keep agent work inside a local env and optionally run inside Docker.
- Remote control via MCP: create, update, validate, run, and inspect routines directly from Claude Code / Codex.
- Optional HTTP trigger API: start a routine from an external system without bypassing the scheduler runtime.
- Faster onboarding: interactive setup bootstraps local config in `.config/routines`.
- Easier authoring: a Textual TUI wizard helps create routines without editing JSON manually.

## Typical Use Cases

- Daily repository triage and issue grooming
- Scheduled content drafting or reporting
- Automated research and summarization jobs
- Recurrent maintenance tasks across multiple projects
- Triggering agents with different models, tools, MCP servers, or startup scripts

## How It Works

Each routine lives in its own folder under `routines/` and contains:

- a scheduler config
- a prompt file
- an optional startup script
- a local working directory for the agent
- execution logs

The scheduler loads those routines, runs enabled tasks on cron schedules, and exposes an MCP endpoint so you can manage them from Claude Code / Codex without touching files directly.

## Key Features

### 1. Scheduler built for agent workflows

- Cron-based task scheduling
- Routine-level and task-level enable/disable
- Per-routine timezone support
- Run-now support for manual execution

### 2. Runtime configuration per routine

- Model selection (`haiku`, `sonnet`, `opus`)
- Built-in tool allowlists
- MCP server selection and MCP tool scoping
- Optional environment variables, plugins, skills, and extra directories

### 3. Isolation options

- Local sandboxed execution
- Optional Docker runtime with custom image
- Optional startup script before the agent runs

### 4. MCP control plane

The MCP server exposes 30 tools for operating the system remotely:

| Category | Tools |
|----------|-------|
| Routine CRUD | `list_routines`, `get_routine`, `add_routine`, `update_routine_config`, `delete_routine`, `rename_routine`, `clone_routine`, `enable_routine`, `disable_routine` |
| Task CRUD | `add_task_to_routine`, `update_task`, `delete_task`, `enable_task`, `disable_task` |
| Import/Export | `export_routine`, `import_routine` |
| Scheduler Control | `reload_routines`, `run_routine_now`, `get_scheduler_status`, `check_filesystem_drift` |
| Monitoring | `list_running_executions`, `get_execution_logs`, `list_execution_history`, `get_last_error` |
| Validation | `validate_routine_config`, `preview_schedule`, `test_startup_script`, `test_prompt`, `list_available_models_tools_plugins`, `suggest_task_id` |

This means you can operate the scheduler from the same agent environment where you already work, instead of switching between code, shell commands, and config files.

## Quick Start

Set up the project and create your first routine in a few minutes.

### 1. Install dependencies

From the `src` directory:

```bash
cd src
uv sync
```

### 2. Run onboarding

```bash
uv run onboard
```

The onboarding flow:

- checks your local environment
- helps install missing dependencies when possible
- configures local Claude/MCP files in `.config/routines`
- avoids relying on `~/.claude*` after setup

### 3. Create your first routine

Recommended path:

```bash
uv run -m cli.create_routine
```

Other options:

- use the MCP `add_routine` tool if the server is already running
- use the authoring reference in [`skills/create-routine.md`](./skills/create-routine.md)

### 4. Start the scheduler and MCP server

```bash
uv run mcp-server
```

This starts the MCP server on:

```text
http://0.0.0.0:8080/mcp
```

If you only want the scheduler without MCP:

```bash
uv run python -c "from scheduler.app import run_scheduler; run_scheduler()"
```

### 5. Connect Claude Code / Codex

Add this MCP server entry to your client config:

```json
{
  "mcpServers": {
    "scheduler": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

To require authentication, set:

```bash
export SCHEDULER_MCP_API_KEY=your-secret-key
```

If `SCHEDULER_MCP_API_KEY` is not set, authentication is disabled.

## Trigger A Routine Via HTTP API

The server also exposes a direct HTTP endpoint for external triggers:

```text
POST /api/routines/{name}/run
```

Request body:

```json
{
  "task_id": "my-task"
}
```

`task_id` is optional. If omitted, all enabled tasks for the routine are triggered, exactly like `run_routine_now`.

Example without auth:

```bash
curl -X POST http://localhost:8080/api/routines/my-routine/run \
  -H "Content-Type: application/json" \
  -d '{"task_id":"my-task"}'
```

Example with auth enabled:

```bash
curl -X POST http://localhost:8080/api/routines/my-routine/run \
  -H "Authorization: Bearer $SCHEDULER_MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"my-task"}'
```

Authentication follows the same rule as the MCP endpoint:

- if `SCHEDULER_MCP_API_KEY` is set, send it in the `Authorization` header
- if `SCHEDULER_MCP_API_KEY` is not set, the endpoint is public on the bound interface

## Routine Anatomy

Each routine lives in its own directory:

```text
routines/<routine-name>/
├── config.json         # Scheduler and runtime configuration
├── prompt.md           # Agent instructions
├── setup.sh            # Optional script executed before the agent starts
├── env/                # Agent working directory
└── logs/               # Execution logs
```

The runtime also accepts prompt filename variants such as `PROMPT.md` and `PROMT.md`.

### Example `config.json`

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "task_id": "my-task",
        "job_name": "my-routine",
        "enabled": true,
        "schedule": {
          "type": "cron",
          "expression": "0 9 * * *"
        },
        "startup_script": "setup.sh"
      }
    ]
  },
  "model_config": {
    "model": "sonnet",
    "allowed_tools": ["Bash", "Read", "Edit"],
    "load_timeout_ms": 60000
  }
}
```

Useful switches:

- `scheduler.enabled = false` disables the whole routine
- `task.enabled = false` disables only one task

## Advanced Capabilities

- Docker runtime: add a `docker` section with `"enabled": true` and an image such as `"node:20"`
- MCP integration: attach external MCP servers and optionally restrict which MCP tools the agent can call
- Startup bootstrap: run `setup.sh` before execution
- Import/export: package routines and move them between environments
- Validation and preview: check prompts, schedules, startup scripts, and config before running

## Why This Is Better Than A Simple Cron Wrapper

Routines is not just "run a script every hour".

It combines:

- scheduling
- agent runtime configuration
- MCP-aware tool selection
- execution monitoring
- validation tooling
- remote operations through an MCP server

That combination is the actual product: a manageable operating layer for recurring AI agent work.

## Project Status

Current stack:

- Python `>=3.13`
- `uv` for dependency management
- APScheduler for scheduling
- FastMCP for the MCP server
- Textual for the creation wizard

## Credits

Created by Gabriele, a 16-year-old from Italy passionate about programming and AI.
