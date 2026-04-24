---
name: create-routine
description: Create or update a routine for this scheduler project. Use when the user asks to create a routine, add a scheduled AI task, configure an autonomous job, or generate routine files under routines/<name>/.
---

You are creating a routine for this project.

Follow these instructions exactly. Do not invent fields that are not supported by the codebase.

Before writing `config.json`, read `skills/routine-config-reference.md` and use it as the source of truth for supported fields, defaults, and runtime behavior.

## Goal

Create a complete routine under `routines/<routine-name>/` that can be discovered and executed by the scheduler in `src/scheduler/`.

A routine is an autonomous AI job with:
- a schedule
- a prompt
- agent options
- optional MCP access
- optional Docker execution
- optional isolated run environment
- optional startup script

## Required Output

For each new routine, create:

```text
routines/<routine-name>/
├── config.json
├── PROMT.md
├── env/
└── logs/
```

Create `setup.sh` only if needed.

Accepted prompt filenames are:
- `PROMT.md`
- `PROMPT.md`
- `promt.md`
- `prompt.md`

Use `PROMT.md` by default to match the existing project convention.

## What To Ask The User First

If the user did not provide enough information, ask only for the missing essentials:
- routine name in kebab-case
- what the routine must do
- when it should run

Ask for these optional settings only when relevant:
- timezone
- model
- tools
- MCP servers
- Docker
- isolated runs
- repo cloning
- startup script

If not specified, use sensible defaults from this project.

## Defaults

Use these defaults unless the user asks otherwise:

- routine directory name: kebab-case
- prompt file: `PROMT.md`
- timezone: `Europe/Rome`
- scheduler enabled: `true`
- model: `sonnet`
- allowed tools: `["Bash", "Read", "Edit"]`
- `load_timeout_ms`: `60000`
- Docker disabled
- isolated runs disabled
- keep executions disabled
- no repo clone
- no startup script

## Directory Rules

Routine files live in:

```text
routines/<routine-name>/
```

Inside that directory:
- `env/` is the agent working directory when runs are not isolated
- `logs/` is used by the scheduler/runtime
- `envs/<timestamp>/` is created automatically only for isolated runs

Always create `env/` and `logs/` up front.

## Supported config.json Shape

Write a JSON object with these top-level sections:
- `scheduler`
- `model_config`
- optional `docker`
- optional `environment`

### Minimal Valid Example

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "job_name": "my-routine",
        "schedule": {
          "type": "cron",
          "expression": "0 9 * * *"
        }
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

### Complete Example With All Supported Options

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "job_name": "github-daily-review",
        "schedule": {
          "type": "cron",
          "expression": "0 9 * * 1-5",
          "metadata": {
            "description": "Review open PRs every weekday morning",
            "retry_on_failure": false
          }
        },
        "startup_script": "setup.sh"
      }
    ]
  },
  "model_config": {
    "model": "sonnet",
    "allowed_tools": ["Bash", "Read", "Edit", "GlobMatch", "GrepSearch", "LS", "View"],
    "disallowed_tools": [],
    "mcp_servers": ["github"],
    "mcp_selected_tools": {
      "github": ["get_pull_request", "list_pull_requests"]
    },
    "max_turns": 12,
    "max_budget_usd": 2.5,
    "add_dirs": [],
    "env": {
      "REPORT_FORMAT": "markdown"
    },
    "skills": null,
    "sandbox": true,
    "plugins": [],
    "thinking": null,
    "effort": null,
    "session_store": null,
    "load_timeout_ms": 60000
  },
  "docker": {
    "enabled": true,
    "image": "node:20",
    "network": "bridge",
    "extra_volumes": [
      "/host/path:/container/path"
    ]
  },
  "environment": {
    "isolated_runs": true,
    "keep_executions": false,
    "clone_repo": "https://github.com/example/project.git",
    "clone_branch": "main"
  }
}
```

## scheduler Section

Use this shape:

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "job_name": "<routine-name>",
        "schedule": {
          "type": "cron",
          "expression": "<cron-expression>"
        }
      }
    ]
  }
}
```

Supported fields:

- `scheduler.enabled`: boolean
- `scheduler.timezone`: IANA timezone string, for example `Europe/Rome`
- `scheduler.tasks`: list of jobs
- `tasks[].job_name`: usually the same as the routine directory name
- `tasks[].schedule.type`: use `"cron"`
- `tasks[].schedule.expression`: cron expression
- `tasks[].schedule.metadata.description`: optional text
- `tasks[].schedule.metadata.retry_on_failure`: optional boolean
- `tasks[].startup_script`: optional relative path, usually `setup.sh`

Notes:
- The runtime looks up the task by `job_name` and cron expression.
- Keep `job_name` stable and simple.
- Prefer one task per routine unless the user explicitly wants more.

## model_config Section

These fields are supported by the runtime sanitizer:

- `tools`
- `allowed_tools`
- `mcp_servers`
- `mcp_selected_tools`
- `max_turns`
- `max_budget_usd`
- `disallowed_tools`
- `model`
- `add_dirs`
- `env`
- `skills`
- `sandbox`
- `plugins`
- `thinking`
- `effort`
- `session_store`
- `load_timeout_ms`

### Recommended fields

Usually set:

```json
{
  "model_config": {
    "model": "sonnet",
    "allowed_tools": ["Bash", "Read", "Edit"],
    "load_timeout_ms": 60000
  }
}
```

### Field-by-field meaning

- `model`: string, usually `sonnet`, `opus`, or `haiku`
- `allowed_tools`: list of built-in tools the agent may use
- `disallowed_tools`: list of blocked tools
- `mcp_servers`: either a list of server names or a pre-resolved object
- `mcp_selected_tools`: map of server name to list of tool names; these are converted into `mcp__<server>__<tool>` entries automatically
- `max_turns`: optional cap on conversation turns
- `max_budget_usd`: optional per-run cost limit
- `add_dirs`: extra directories to grant access to
- `env`: environment variables passed to the agent runtime
- `skills`: optional skill configuration passed through as-is
- `sandbox`: boolean or null; if omitted/null the runtime defaults to sandboxed mode
- `plugins`: optional plugin list
- `thinking`: optional advanced agent config, passed through as-is
- `effort`: optional advanced agent config, passed through as-is
- `session_store`: optional advanced agent config, passed through as-is
- `load_timeout_ms`: positive integer timeout; when sandbox is enabled, runtime may raise it to at least `300000`

### Tool Defaults

If `allowed_tools` ends up empty, the runtime falls back to:

```json
["Bash", "Read", "Edit"]
```

### MCP Rules

Use `mcp_servers` only when the routine really needs external tools/resources.

Preferred form:

```json
{
  "mcp_servers": ["notion", "github"]
}
```

Optional tool restriction:

```json
{
  "mcp_servers": ["github"],
  "mcp_selected_tools": {
    "github": ["get_pull_request", "list_pull_requests"]
  }
}
```

Notes:
- If you provide a list, the runtime resolves server names from project MCP config.
- If you provide a dict, the runtime uses it directly.
- `mcp_selected_tools` only matters when paired with matching servers.

## docker Section

Use only when the agent must run through Docker.

Supported fields:
- `enabled`
- `image`
- `network`
- `extra_volumes`

Example:

```json
{
  "docker": {
    "enabled": true,
    "image": "node:20",
    "network": "bridge",
    "extra_volumes": [
      "/abs/host/path:/workspace"
    ]
  }
}
```

Notes:
- When Docker is enabled, the runtime generates a wrapper script automatically.
- The working directory is mounted into the container as `/env`.
- Additional volumes must already be valid Docker volume mappings.

## environment Section

Use for execution isolation and repo preparation.

Supported fields:
- `isolated_runs`
- `keep_executions`
- `clone_repo`
- `clone_branch`

Example:

```json
{
  "environment": {
    "isolated_runs": true,
    "keep_executions": true,
    "clone_repo": "https://github.com/example/project.git",
    "clone_branch": "main"
  }
}
```

Behavior:
- `isolated_runs: true` creates a fresh `envs/<timestamp>/` working directory for each run
- if `clone_repo` is set and runs are isolated, the repo is cloned into each fresh execution directory
- if `clone_repo` is set and runs are not isolated, the repo is cloned into `env/` only if that directory is empty
- `keep_executions: false` deletes isolated execution directories after the run
- `keep_executions` matters only when `isolated_runs` is enabled

## PROMT.md Rules

The prompt must be explicit, operational, and self-contained.

Good prompt characteristics:
- says exactly what to inspect
- says exactly what output to produce
- says where to write results
- says what to avoid
- says how to handle errors

Recommended prompt structure:

```md
# Objective
Explain the goal in one sentence.

# Inputs
List the files, APIs, directories, or MCP sources to inspect.

# Tasks
List the steps the agent must execute.

# Output
Specify the exact output format and destination files.

# Constraints
State limits, exclusions, and safety rules.
```

### Example Prompt

```md
# Objective
Review the current repository status and produce a concise daily engineering report.

# Inputs
- Inspect the git working tree
- Read recent files under `src/`
- Check open issues only if GitHub MCP is available

# Tasks
1. Summarize the main code changes since the previous run.
2. Identify risky areas or failing assumptions.
3. Write a short report in Markdown.

# Output
Write the final report to `report.md` in the current working directory.

# Constraints
- Do not modify application code.
- Do not commit or push changes.
- Keep the report under 300 words.
```

## setup.sh Rules

Create `setup.sh` only if the routine needs preparation before the agent starts.

Typical uses:
- create folders
- fetch data
- prepare fixtures
- print execution markers
- install lightweight prerequisites already available on the system

Use:

```sh
#!/usr/bin/env sh
set -eu
echo "Routine <routine-name> started in $(pwd)"
```

Important:
- on Linux, prefer `.sh`
- if you create it, make it executable
- reference it in `tasks[0].startup_script`

## Cron Quick Reference

```text
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sun=0)
* * * * *
```

Common expressions:
- `0 9 * * *` every day at 09:00
- `0 9 * * 1-5` weekdays at 09:00
- `*/30 * * * *` every 30 minutes
- `0 9,18 * * *` twice daily
- `0 0 * * 0` every Sunday at midnight

## Creation Procedure

When asked to create a routine, execute this flow:

1. Determine the routine name and convert it to kebab-case if needed.
2. Create `routines/<routine-name>/`.
3. Create `env/` and `logs/`.
4. Write `config.json` using only supported fields.
5. Write `PROMT.md`.
6. If needed, write `setup.sh` and make it executable.
7. Validate that `config.json` is valid JSON.
8. Summarize what was created and which defaults were assumed.

## Update Procedure

When asked to modify an existing routine:

1. Read the current `config.json` and prompt file first.
2. Preserve user settings unless the request explicitly changes them.
3. Do not remove advanced fields just because they were not mentioned.
4. If changing schedule or runtime behavior, explain the impact briefly.

## Validation Checklist

Before finishing, verify all of the following:

- the routine directory exists
- `config.json` exists and is valid JSON
- `scheduler.enabled` is boolean
- `scheduler.tasks[0].schedule.type` is `"cron"`
- `scheduler.tasks[0].schedule.expression` is present
- `PROMT.md` exists and is non-empty
- `env/` exists
- `logs/` exists
- if `startup_script` is declared, the script file exists
- if Docker is enabled, `docker.enabled` is `true`
- if `clone_branch` is set, `clone_repo` is also set

## Guardrails

Do not:
- invent unsupported top-level sections
- omit `scheduler.tasks`
- use non-kebab-case routine directory names unless explicitly requested
- create empty prompts
- add Windows-only `.bat` scripts on Linux unless the user explicitly asks for them
- overwrite unrelated user changes in other routines

## Practical Notes

- The scheduler discovers routines by scanning `routines/` for subdirectories with `config.json`.
- The runtime reads prompt files using several accepted spellings, but `PROMT.md` matches the project convention.
- If `sandbox` is missing or null, the runtime enables sandbox mode automatically.
- If `allowed_tools` is omitted or empty at runtime, the default tool set becomes `["Bash", "Read", "Edit"]`.
- MCP tool names are auto-expanded from `mcp_selected_tools` into names like `mcp__server__tool`.

When you finish, tell the user:
- which routine was created or updated
- which files were written
- which defaults you assumed
- any optional features left disabled
