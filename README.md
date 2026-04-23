# AI Routines Scheduler

Automated scheduler that runs Claude agent routines on cron schedules, with an MCP server for remote management via Claude Code / Codex.

---

## Features

- Flexible Scheduling: Use Cron expressions to decide when your agents should start.
- Secure Isolation: Support for Docker and isolated execution environments (ephemeral envs).
- MCP Integration: Connect your MCP servers (GitHub, Notion, Google Drive, etc.) to enhance your routines.
- MCP Control Plane: 30 MCP tools to manage routines, tasks, scheduler, and execution monitoring from Claude Code / Codex.
- Automatic Setup: An onboarding script guides you through the initial configuration.
- TUI Wizard: Create new routines visually and easily.

---

## Quick Start

Follow these steps to configure the project and create your first routine in less than 2 minutes.

### 1. Installation and Setup
Navigate to the `src` folder and run the automatic onboarding:
```bash
cd src
uv sync
uv run onboard
```
The onboarding will install dependencies, check your environment, and configure the necessary keys.

### 2. Create your first Routine
There are three ways to create a routine:
- Visual (Recommended): Run the TUI wizard:
  ```bash
  uv run -m cli.create_routine
  ```
- With AI: If you are using this guide with an AI agent, use the `skills/create-routine/.md` skill.
- Via MCP: If the MCP server is running, use the `add_routine` tool from Claude Code / Codex.

### 3. Start the Scheduler + MCP Server
```bash
uv run mcp-server
```
Starts both the scheduler and the MCP server on `http://0.0.0.0:8080/mcp`.

To start only the scheduler without MCP:
```bash
uv run python -c "from scheduler.app import run_scheduler; run_scheduler()"
```

### 4. Connect Claude Code / Codex
Add to your Claude Code MCP settings:
```json
{
  "mcpServers": {
    "scheduler": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Set `SCHEDULER_MCP_API_KEY` env var to require authentication. If unset, auth is disabled.

---

## Routine Anatomy

Each routine lives in its dedicated folder inside `routines/`:

```text
routines/<routine-name>/
├── config.json      # Technical configuration (schedule, model, tools)
├── PROMT.md         # Instructions (system prompt) for the agent
├── setup.sh         # (Optional) Script to run before the agent
├── env/             # Agent working directory
└── logs/            # Logs of past executions
```

### config.json

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

- `task.enabled`: set to `false` to disable a single task without removing it
- `scheduler.enabled`: set to `false` to disable the entire routine

---

## MCP Tools

The MCP server exposes 30 tools for managing the scheduler from Claude Code / Codex:

| Category | Tools |
|----------|-------|
| Routine CRUD | `list_routines`, `get_routine`, `add_routine`, `update_routine_config`, `delete_routine`, `rename_routine`, `clone_routine`, `enable_routine`, `disable_routine` |
| Task CRUD | `add_task_to_routine`, `update_task`, `delete_task`, `enable_task`, `disable_task` |
| Import/Export | `export_routine`, `import_routine` |
| Scheduler Control | `reload_routines`, `run_routine_now`, `get_scheduler_status`, `check_filesystem_drift` |
| Monitoring | `list_running_executions`, `get_execution_logs`, `list_execution_history`, `get_last_error` |
| Validation | `validate_routine_config`, `preview_schedule`, `test_startup_script`, `test_prompt`, `list_available_models_tools_plugins`, `suggest_task_id` |

---

## Advanced Functions

- Docker: You can run the agent inside a container by adding the `"docker": {"enabled": true, "image": "node:20"}` section.
- Git Clone: You can instruct the routine to clone a GitHub repository before starting work in the environment section.
- MCP: Enable external servers by adding their names in `mcp_servers`.
- Task-level enable/disable: Set `enabled: false` on individual tasks to skip them without removing.

---

## Credits

Created by Gabriele, a 16-year-old from Italy passionate about programming and AI.
