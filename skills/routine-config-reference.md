---
name: routine-config-reference
description: Reference for building a valid routines/<name>/config.json in this scheduler project. Use before calling MCP add_routine or when editing config fields.
---

Use this reference before creating or updating a routine config.

Do not invent fields that are not documented here.

If a user asks to create a routine through MCP, first build a config that matches this document, then optionally validate it with `validate_routine_config`, and only then call `add_routine`.

## Scope

This document describes the real `config.json` shape accepted by the current codebase:
- what is required by validation
- what is read at runtime
- what is optional but preserved on disk
- what defaults are injected when fields are omitted

The routine config lives at:

```text
routines/<routine-name>/config.json
```

## Top-Level Shape

`config.json` is a JSON object with:
- required `scheduler`
- optional `model_config`
- optional `docker`
- optional `environment`

Minimal valid example:

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "task_id": "task-0",
        "job_name": "daily-review",
        "enabled": true,
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

## scheduler

This section is required.

Supported fields:

- `scheduler.enabled`: required boolean. Enables or disables the whole routine.
- `scheduler.timezone`: optional IANA timezone string. Example: `Europe/Rome`. Defaults to `UTC` in validation and summary code if missing.
- `scheduler.tasks`: optional array. Use at least one task for a real routine.

Each task supports:

- `task_id`: optional string. Strongly recommended. If omitted, some parts of the code fall back to `job_name` or `task-<index>`.
- `job_name`: optional string. Usually equal to the routine directory name.
- `enabled`: optional boolean. Defaults to `true` when missing.
- `schedule`: required object for any runnable task.
- `startup_script`: optional string path relative to the routine directory, for example `setup.sh`.

Supported `schedule` fields:

- `type`: required string. Must be exactly `"cron"`.
- `expression`: required cron string, for example `0 9 * * *`.
- `metadata`: optional object. It is preserved on disk but currently not used by the runtime scheduler.

Recommended task example:

```json
{
  "task_id": "task-0",
  "job_name": "daily-review",
  "enabled": true,
  "schedule": {
    "type": "cron",
    "expression": "0 9 * * 1-5"
  },
  "startup_script": "setup.sh"
}
```

Notes:
- `validate_routine_config` checks `scheduler`, task objects, `schedule.type`, `schedule.expression`, and timezone validity.
- The runtime matches a scheduled execution mainly by `job_name` and cron expression.
- `startup_script` is read from the task entry, not from `model_config`.

## model_config

This section is optional in storage, but almost always useful in practice.

Recognized fields:

- `model`: string. Valid values enforced by validation: `sonnet`, `opus`, `haiku`. Default: `sonnet`.
- `tools`: preserved but not actively interpreted in the current runtime path.
- `allowed_tools`: array of strings. Default sanitized value: `[]`, but at runtime it falls back to project defaults if still empty.
- `disallowed_tools`: array of strings. Default: `[]`.
- `mcp_servers`: array of server names or a server-definition object. Default: `[]`.
- `mcp_selected_tools`: object mapping server name to array of tool names. Default: `{}`.
- `max_turns`: optional number or null.
- `max_budget_usd`: optional number or null.
- `add_dirs`: array of extra directories. Default: `[]`.
- `env`: object of environment variables for the agent. Default: `{}`.
- `skills`: optional value or null. Preserved and forwarded.
- `sandbox`: optional boolean, but the current runtime forces it to `true`.
- `plugins`: array. Default: `[]`.
- `thinking`: optional value or null.
- `effort`: optional value or null.
- `session_store`: optional value or null.
- `load_timeout_ms`: positive integer. Default: `60000`. If sandbox is enabled, the runtime raises it to at least `300000`.

Runtime defaults injected by `RoutineConfig`:

```json
{
  "tools": null,
  "allowed_tools": [],
  "mcp_servers": [],
  "mcp_selected_tools": {},
  "max_turns": null,
  "max_budget_usd": null,
  "disallowed_tools": [],
  "model": "sonnet",
  "add_dirs": [],
  "env": {},
  "skills": null,
  "sandbox": true,
  "plugins": [],
  "thinking": null,
  "effort": null,
  "session_store": null,
  "load_timeout_ms": 60000
}
```

Important behavior:

- `sandbox` is currently forced to `true` even if the file says otherwise.
- If `allowed_tools` ends up empty, the runtime falls back to `["Bash", "Read", "Edit"]`.
- If `mcp_servers` is a list of names, the runtime resolves them from discovered local MCP servers before starting the agent.
- If `mcp_selected_tools` is present, the runtime automatically expands allowed tools into names like `mcp__github__get_pull_request`.
- If a server is selected without explicit tool names, the runtime allows the namespace prefix form `mcp__server__`.

Recommended example:

```json
{
  "model_config": {
    "model": "sonnet",
    "allowed_tools": ["Bash", "Read", "Edit", "LS", "GrepSearch"],
    "mcp_servers": ["github"],
    "mcp_selected_tools": {
      "github": ["get_pull_request", "list_pull_requests"]
    },
    "max_turns": 12,
    "max_budget_usd": 2.5,
    "env": {
      "REPORT_FORMAT": "markdown"
    },
    "load_timeout_ms": 60000
  }
}
```

## docker

This section is optional.

Supported fields:

- `docker.enabled`: boolean. When true, the agent is executed through a generated Docker wrapper.
- `docker.image`: string. Default runtime fallback: `node:20`.
- `docker.network`: string. Default runtime fallback: `bridge`.
- `docker.extra_volumes`: array of Docker volume strings like `"/host/path:/container/path"`.

Example:

```json
{
  "docker": {
    "enabled": true,
    "image": "node:20",
    "network": "bridge",
    "extra_volumes": [
      "/host/path:/container/path"
    ]
  }
}
```

Notes:
- When Docker is enabled, the runtime creates a wrapper script and a minimal Claude settings payload under `.runtime/scheduler/<routine>/`.
- Some local auth and MCP settings are propagated into the container runtime automatically.

## environment

This section is optional.

Supported fields:

- `environment.isolated_runs`: boolean. Default: `false`.
- `environment.keep_executions`: boolean. Default: `false`.
- `environment.clone_repo`: string Git URL. Optional.
- `environment.clone_branch`: string. Default runtime fallback: `main`.

Behavior:

- If `isolated_runs` is `true`, each execution happens in `routines/<name>/envs/<timestamp>/`.
- If `clone_repo` is set with `isolated_runs=true`, the repo is cloned fresh into each ephemeral execution directory.
- If `isolated_runs` is `false`, the routine uses `routines/<name>/env/`.
- If `clone_repo` is set and `env/` is still empty, the initial clone happens there once.
- If `keep_executions` is `false`, ephemeral execution directories are removed after the run.

Example:

```json
{
  "environment": {
    "isolated_runs": true,
    "keep_executions": false,
    "clone_repo": "https://github.com/example/project.git",
    "clone_branch": "main"
  }
}
```

## Safe Creation Checklist

Before calling MCP `add_routine`, make sure:

1. The routine name is kebab-case and matches the directory you want under `routines/`.
2. `scheduler.enabled` is present.
3. `scheduler.tasks` is an array and each runnable task has `schedule.type = "cron"` and a valid `schedule.expression`.
4. `scheduler.timezone` is a valid IANA timezone if provided.
5. `model_config.model` is one of `sonnet`, `opus`, `haiku` if provided.
6. `startup_script`, if present, points to a file inside the routine directory.
7. `mcp_servers` contains only server names that exist in the local Claude/MCP configuration.
8. The prompt is provided separately to MCP `add_routine` as the `prompt` argument.

## Important Distinctions

- `add_routine` writes `PROMPT.md`, while the runtime can read `PROMPT.md`, `PROMT.md`, `prompt.md`, or `promt.md`.
- `validate_routine_config` validates only part of the schema. Some optional fields are runtime-only and are not deeply validated.
- Unknown fields are usually preserved by CRUD services, but they should not be invented because the runtime may ignore them completely.
- If you need a unique task id for an existing routine, use `suggest_task_id`.

## Best-Practice Template

Use this when no special requirements are given:

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "task_id": "task-0",
        "job_name": "<routine-name>",
        "enabled": true,
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
