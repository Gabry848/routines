---
name: new-routine
description: Create a new routine for the routines scheduler. Use when user says "create routine", "new routine", "aggiungi routine", "nuova routine", or "/new-routine".
---

You are creating a new routine for this project's automated scheduler.

## Project Context

Routines live under the `routines/<routine-name>/` directory relative to the project root.
The scheduler (in `src/scheduler/`) discovers directories there, reads `config.json`, and runs Claude via `claude_agent_sdk`.

Each routine directory contains:
- `config.json` — scheduler config + Claude agent options
- `PROMT.md` — the prompt sent to the Claude agent (filenames `PROMT.md`, `PROMPT.md`, `promt.md`, `prompt.md` all accepted)
- `env/` — working directory for the agent (agent's `cwd` is set here)
- `setup.sh` — optional startup script (runs before agent; use `.sh` not `.bat` on Linux)
- `logs/` — auto-created output directory

## Steps

### 1. Gather requirements from user

Ask the user:
- **Routine name** (kebab-case, e.g. `notion-backlog-report`) — used as directory name
- **What the routine should do** — this becomes the `PROMT.md` content
- **Schedule** — cron expression (default: ask when and how often)
- **Model** — default `sonnet`
- **MCP servers needed** — e.g. `["notion"]` or empty list
- **Startup script needed?** — default no

### 2. Create directory structure

```
routines/<routine-name>/
routines/<routine-name>/env/
routines/<routine-name>/logs/
```

### 3. Create config.json

Use this template, filling in the gathered values:

```json
{
  "model_config": {
    "mcp_servers": [],
    "model": "sonnet",
    "allowed_tools": [],
    "load_timeout_ms": 60000
  },
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "job_name": "<routine-name>",
        "schedule": {
          "type": "cron",
          "expression": "<cron-expression>",
          "metadata": {
            "description": "<short description>",
            "retry_on_failure": false
          }
        },
        "startup_script": "setup.sh"
      }
    ]
  }
}
```

Key `model_config` fields (all optional, include only what's needed):
- `mcp_servers`: list of MCP server names, e.g. `["notion"]`
- `model`: `"sonnet"` (default), `"opus"`, `"haiku"`
- `allowed_tools`: list of tool names the agent can use, default `["Bash", "Read", "Edit"]`
- `disallowed_tools`: tools to explicitly block
- `max_turns`: max conversation turns
- `max_budget_usd`: cost cap

### 4. Create PROMT.md

Write the prompt in the user's language (Italian or English based on context).
Be specific and actionable — this is what the Claude agent executes autonomously.

### 5. Create setup.sh (if needed)

```sh
#!/usr/bin/env sh
set -eu
echo "Routine <routine-name> avviata in $(pwd)"
```

Make it executable with `chmod +x`.

### 6. Verify

- Confirm all files exist
- Validate `config.json` is valid JSON
- Show the user a summary of what was created

## Cron Expression Quick Reference

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sun=0)
│ │ │ │ │
* * * * *
```

Common patterns:
- `0 9 * * *` — every day at 09:00
- `0 9 * * 1-5` — weekdays at 09:00
- `*/30 * * * *` — every 30 minutes
- `0 9,18 * * *` — twice daily at 09:00 and 18:00
