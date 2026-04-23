# AI Routines Scheduler

Welcome to AI Routines Scheduler. This project allows you to create and schedule AI "mini-agents" (Routines) that perform tasks autonomously using Claude.

---

## Features

- Flexible Scheduling: Use Cron expressions to decide when your agents should start.
- Secure Isolation: Support for Docker and isolated execution environments (ephemeral envs).
- MCP Integration: Connect your MCP servers (GitHub, Notion, Google Drive, etc.) to enhance your routines.
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
- Manual: Create the files following the anatomy described below.

### 3. Start the Scheduler
Once the routine is created, start the main program to queue it:
```bash
uv run main.py
```
The scheduler will remain active and start the routines at the pre-established times.

---

## Routine Anatomy

Each routine lives in its dedicated folder inside `routines/`. Here is how it must be structured to function correctly:

```text
routines/<routine-name>/
├── config.json      # Technical configuration (schedule, model, tools)
├── PROMT.md         # Instructions (system prompt) for the agent
├── setup.sh         # (Optional) Script to run before the agent
├── env/             # Agent working directory
└── logs/            # Logs of past executions
```

### Manual Configuration (config.json)
A minimal example of a valid configuration:

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

---

## Advanced Functions

- Docker: You can run the agent inside a container by adding the "docker": {"enabled": true, "image": "node:20"} section.
- Git Clone: You can instruct the routine to clone a GitHub repository before starting work in the environment section.
- MCP: Enable external servers by adding their names in mcp_servers.

---

## Credits

Created by Gabriele, a 16-year-old from Italy passionate about programming and AI.

---

For more details, consult the files in scheduler/ to deepen your understanding of the engine.
