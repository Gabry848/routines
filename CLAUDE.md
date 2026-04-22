# Routines Project

Automated scheduler that runs Claude agent routines on cron schedules.

## Structure

- `routines/` — routine definitions (each subfolder = one routine)
- `src/scheduler/` — Python scheduler engine using `claude_agent_sdk`
- `src/scheduler/constants.py` — `ROUTINES_PATH` points to `routines/`

## Routine anatomy

Each routine folder (`routines/<name>/`) contains:
- `config.json` — scheduler config + model config (see `src/scheduler/loader.py`, `src/scheduler/routine.py`)
- `PROMT.md` (or `PROMPT.md`, `prompt.md`, `promt.md`) — prompt sent to Claude
- `env/` — agent working directory (`cwd`)
- `logs/` — auto-created execution logs
- `setup.sh` — optional pre-execution script

## Creating routines

Use the `/new-routine` skill or follow the pattern in existing routines (e.g. `notion-backlog-report`).

## Key code paths

- Discovery: `src/scheduler/loader.py:discover_routines()` scans `routines/` for subdirs
- Config loading: `src/scheduler/loader.py:load_jobs()` reads `config.json` per routine
- Execution: `src/scheduler/routine.py:Routine.start()` loads config, runs startup script, launches Claude agent
- Agent: `src/scheduler/agent.py:ClaudeAgent.run()` streams Claude output and writes logs
