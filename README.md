# Routines

Automated routine scheduler powered by Claude. Define recurring AI tasks — like Anthropic's Claude Code routines — and run them on cron schedules autonomously.

## What are Routines?

Routines are **automated, recurring tasks executed by a Claude AI agent**. Think of them as cron jobs where the worker is an AI assistant instead of a script.

You define **what** the AI should do (via a prompt), **when** it should run (via cron), and **which tools** it has access to. The scheduler handles the rest.

### Use cases

| Example | What it does |
|---|---|
| `notion-backlog-report` | Daily backlog digest from Notion database |
| `notizie` | News analysis at scheduled times |
| Code review bot | Reviews PRs every morning |
| Email summarizer | Summarizes unread emails hourly |
| Server monitor | Checks health endpoints every 30 min |
| Documentation updater | Syncs docs from code changes weekly |

## How it works

```
routines/
├── notion-backlog-report/    ← one routine
│   ├── config.json           ← schedule + agent config
│   ├── PROMT.md              ← the prompt sent to Claude
│   ├── env/                  ← agent working directory
│   ├── setup.sh              ← optional pre-run script
│   └── logs/                 ← execution logs (auto-created)
├── notizie/                  ← another routine
└── example/                  ← minimal example
```

1. **Scheduler** (`src/scheduler/`) scans `routines/` for subdirectories
2. Each directory with a valid `config.json` is a routine
3. At the scheduled time, it spins up a Claude agent with the configured options
4. The agent executes the prompt in `PROMT.md` with access to specified tools and MCP servers
5. Logs are written to `logs/`

## Quick start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- A Claude API key or Claude Code setup

### Install and run

```bash
cd src
uv sync
uv run onboard
uv run python main.py
```

`onboard` runs dependency checks, proposes automatic installs when possible, and saves the Claude/MCP configuration used by the scheduler into `.config/routines`.
The scheduler then discovers all enabled routines and runs them on their cron schedules without reading `~/.claude*` at runtime.

## Routine anatomy

### config.json

```json
{
  "model_config": {
    "model": "sonnet",
    "mcp_servers": ["notion"],
    "allowed_tools": ["Bash", "Read", "Edit"],
    "load_timeout_ms": 60000
  },
  "scheduler": {
    "enabled": true,
    "timezone": "Europe/Rome",
    "tasks": [
      {
        "job_name": "my-routine",
        "schedule": {
          "type": "cron",
          "expression": "0 9 * * *",
          "metadata": {
            "description": "Runs daily at 9am",
            "retry_on_failure": false
          }
        },
        "startup_script": "setup.sh"
      }
    ]
  }
}
```

**model_config** — Claude agent options:
| Field | Default | Description |
|---|---|---|
| `model` | `sonnet` | Claude model (`sonnet`, `opus`, `haiku`) |
| `mcp_servers` | `[]` | MCP servers the agent can use |
| `allowed_tools` | `["Bash","Read","Edit"]` | Tools the agent can access |
| `max_turns` | — | Max conversation turns |
| `max_budget_usd` | — | Cost cap per run |

**scheduler** — when to run:
| Field | Description |
|---|---|
| `enabled` | `true` to activate |
| `timezone` | IANA timezone (e.g. `Europe/Rome`) |
| `tasks[].schedule.expression` | Cron expression |
| `tasks[].startup_script` | Script to run before agent starts |

### PROMT.md

The prompt the Claude agent receives. Be specific and actionable — the agent runs autonomously.

Example:
```markdown
Connect to the Notion database "My Project".
List all open tasks grouped by priority.
Write a summary to logs/report_{{date}}.md.
```

### setup.sh (optional)

Runs before the Claude agent. Use for environment prep:

```sh
#!/usr/bin/env sh
set -eu
echo "Routine started at $(date)"
mkdir -p output
```

## Creating a routine

### Option 1: Using the skill (recommended)

The project includes a Claude Code skill that guides you through creating a new routine.

#### Install the skill on your Claude Code agent

Copy the skill into your `.claude/skills/` directory:

```bash
# From the project root
mkdir -p .claude/skills
cp skills/new-routine.md .claude/skills/new-routine/SKILL.md
```

Then in Claude Code, type:

```
/new-routine
```

The skill will ask you for the routine name, what it should do, the schedule, and handle file creation.

#### Install globally (available in all projects)

```bash
mkdir -p ~/.claude/skills/new-routine
cp skills/new-routine.md ~/.claude/skills/new-routine/SKILL.md
```

### Option 2: Manual creation

1. Create the directory structure:

```bash
mkdir -p routines/my-routine/env routines/my-routine/logs
```

2. Write `routines/my-routine/config.json` with schedule and model config (see template above).

3. Write `routines/my-routine/PROMT.md` with your prompt.

4. (Optional) Create `routines/my-routine/setup.sh` and make it executable:

```bash
chmod +x routines/my-routine/setup.sh
```

5. Restart the scheduler — it auto-discovers new routines.

### Cron expression reference

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sun=0)
* * * * *
```

| Expression | Schedule |
|---|---|
| `0 9 * * *` | Every day at 09:00 |
| `0 9 * * 1-5` | Weekdays at 09:00 |
| `*/30 * * * *` | Every 30 minutes |
| `0 9,18 * * *` | Twice daily |
| `0 0 * * 0` | Every Sunday at midnight |

## Architecture

```
src/
├── main.py                 # Entry point
├── scheduler/
│   ├── app.py              # Scheduler bootstrap
│   ├── engine.py           # Cron engine
│   ├── loader.py           # Discovers + loads routines
│   ├── routine.py          # Routine execution logic
│   ├── agent.py            # Claude agent wrapper
│   ├── cron.py             # Cron parsing
│   └── constants.py        # Paths, defaults
└── pyproject.toml
```

Flow: `main.py` → `app.py` → `loader.py` discovers routines → `engine.py` schedules them → `routine.py` executes each run → `agent.py` runs Claude via `claude-agent-sdk`.
