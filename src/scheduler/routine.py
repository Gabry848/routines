import json
import os
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from .agent import ClaudeAgent
from .constants import *


class RoutineConfig:
    MODEL_CONFIG_DEFAULTS: dict[str, Any] = {
        "tools": None,
        "allowed_tools": [],
        "mcp_servers": {},
        "max_turns": None,
        "max_budget_usd": None,
        "disallowed_tools": [],
        "model": DEFAULT_MODEL,
        "add_dirs": [],
        "env": {},
        "skills": None,
        "sandbox": None,
        "plugins": [],
        "thinking": None,
        "effort": None,
        "session_store": None,
        "load_timeout_ms": 60000,
    }

    def __init__(self, routine_dir_name: str) -> None:
        self.routine_dir_name = routine_dir_name
        self.routine_path = ROUTINES_PATH / routine_dir_name
        self.config_data: dict[str, Any] = {}
        self.model_config: dict[str, Any] = {}
        self.prompt_text = ""

    def load(self) -> "RoutineConfig":
        self._load_config_json()
        self._load_prompt_file()
        raw_model_config = self.config_data.get("model_config", {})
        self.model_config = self._sanitize_model_config(raw_model_config)
        return self

    def _sanitize_model_config(self, raw_model_config: Any) -> dict[str, Any]:
        if not isinstance(raw_model_config, dict):
            raw_model_config = {}

        sanitized = dict(self.MODEL_CONFIG_DEFAULTS)

        for key in self.MODEL_CONFIG_DEFAULTS:
            if key not in raw_model_config:
                continue

            value = raw_model_config[key]

            if key in {"allowed_tools", "disallowed_tools", "add_dirs", "plugins"}:
                sanitized[key] = value if isinstance(value, list) else []
                continue

            if key in {"mcp_servers", "env"}:
                sanitized[key] = value if isinstance(value, dict) else {}
                continue

            if key == "model":
                sanitized[key] = value if isinstance(value, str) and value else DEFAULT_MODEL
                continue

            if key == "load_timeout_ms":
                sanitized[key] = value if isinstance(value, int) and value > 0 else 60000
                continue

            if key in {"max_turns", "max_budget_usd", "skills", "sandbox", "session_store", "tools", "thinking", "effort"}:
                sanitized[key] = value

        return sanitized

    def _load_config_json(self) -> None:
        config_path = self.routine_path / "config.json"
        if not config_path.exists():
            self.config_data = {}
            return

        with config_path.open("r", encoding="utf-8") as config_file:
            loaded = json.load(config_file)

        self.config_data = loaded if isinstance(loaded, dict) else {}

    def _load_prompt_file(self) -> None:
        prompt_candidates = PROMT_FILENAME_CANDIDATES
        self.prompt_text = ""

        for filename in prompt_candidates:
            prompt_path = self.routine_path / filename
            if prompt_path.exists():
                self.prompt_text = prompt_path.read_text(encoding="utf-8")
                return

    def get_timezone(self, default: str = "UTC") -> str:
        scheduler = self.config_data.get("scheduler", {})
        if not isinstance(scheduler, dict):
            return default
        timezone = scheduler.get("timezone", default)
        return timezone if isinstance(timezone, str) and timezone else default

    def get_task_for_job(self, job_name: str, cron_expression: str) -> dict[str, Any] | None:
        scheduler = self.config_data.get("scheduler", {})
        if not isinstance(scheduler, dict):
            return None

        tasks = scheduler.get("tasks", [])
        if not isinstance(tasks, list):
            return None

        for task in tasks:
            if not isinstance(task, dict):
                continue
            schedule = task.get("schedule", {})
            if (
                schedule.get("type") == "cron"
                and schedule.get("expression") == cron_expression
                and (task.get("job_name") == job_name or self.routine_dir_name == job_name)
            ):
                return task

        return None
    
    def startup_script_for(self, job_name: str, cron_expression: str) -> str | None:
        task = self.get_task_for_job(job_name, cron_expression)
        startup_script = task.get("startup_script") if isinstance(task, dict) else None
        return startup_script if isinstance(startup_script, str) and startup_script else None

    def build_agent_options(self) -> ClaudeAgentOptions:
        options_payload = dict(self.model_config)
        
        env_path = ROUTINES_PATH / self.routine_dir_name / "env"
        options_payload["cwd"] = env_path
        options_payload["model"] = options_payload.get("model") or DEFAULT_MODEL
        options_payload["allowed_tools"] = options_payload.get("allowed_tools") or DEFAULT_TOOLS
        if options_payload.get("sandbox") is None:
            options_payload["sandbox"] = True

        docker_config = self.config_data.get("docker", {})
        if docker_config.get("enabled"):
            image = docker_config.get("image", "node:20")
            network = docker_config.get("network", "bridge")
            extra_volumes = docker_config.get("extra_volumes", [])
            
            # Scrive il wrapper una volta sola nella directory root del progetto Python
            # anziché dentro le cartelle env delle varie routine.
            wrapper_path = Path(__file__).parent / "docker_wrapper.sh"
            
            volumes_args = []
            for vol in extra_volumes:
                volumes_args.append(f"-v {vol}")
            
            # Inietteremo queste impostazioni tramite variabili d'ambiente fornite all'SDK
            script_content = f"""#!/bin/bash
# Wrapper globale per eseguire l'agent in Docker
echo ">>> [Docker Wrapper] Esecuzione in container con network=$CLAUDE_DOCKER_NETWORK image=$CLAUDE_DOCKER_IMAGE" >&2

exec docker run -i --rm \\
  --network "$CLAUDE_DOCKER_NETWORK" \\
  -e HOME=/root \\
  -v "$PWD:/env" \\
  -v "$HOME/.claude.json:/root/.claude.json:ro" \\
  -v "$HOME/.claude:/root/.claude" \\
  $CLAUDE_DOCKER_VOLUMES \\
  -w /env \\
  "$CLAUDE_DOCKER_IMAGE" npx -y @anthropic-ai/claude-code@latest "$@"
"""
            wrapper_path.write_text(script_content)
            wrapper_path.chmod(0o755)
            
            options_payload["cli_path"] = str(wrapper_path)
            
            # Passiamo le opzioni variabili al wrapper iniettandole nell'env del thread locale Python
            custom_env = options_payload.get("env") or {}
            custom_env["CLAUDE_DOCKER_NETWORK"] = network
            custom_env["CLAUDE_DOCKER_IMAGE"] = image
            custom_env["CLAUDE_DOCKER_VOLUMES"] = " ".join(volumes_args)
            options_payload["env"] = custom_env

        return ClaudeAgentOptions(**options_payload)


class Routine:
    def __init__(
        self,
        routine_dir_name: str,
        routine_name: str,
        timezone: str,
        cron_expression: str,
    ) -> None:
        self.routine_dir_name = routine_dir_name
        self.routine_name = routine_name
        self.timezone = timezone
        self.cron_expression = cron_expression

    def _setup(self, startup_script: str | None) -> None:
        """Logic to execute before each routine start."""
        if not startup_script:
            return

        routine_path = ROUTINES_PATH / self.routine_dir_name
        startup_path = Path(startup_script)
        if not startup_path.is_absolute():
            startup_path = routine_path / startup_path

        if not startup_path.exists():
            print(f"startup script non trovato: {startup_path}")
            return

        if startup_path.stat().st_size == 0:
            print(f"startup script vuoto, skip: {startup_path}")
            return

        # .bat scripts are Windows-specific; skip on non-Windows hosts.
        if startup_path.suffix.lower() == ".bat" and os.name != "nt":
            print(f"startup script .bat non supportato su questo OS: {startup_path}")
            return

        subprocess.run(
            str(startup_path),
            shell=True,
            cwd=routine_path / "env",
            check=False,
        )

    async def start(self) -> None:
        """Logic to execute when the routine is triggered."""
        print(f"routine partita[{self.routine_name}]")

        runtime_config = RoutineConfig(self.routine_dir_name).load()
        startup_script = runtime_config.startup_script_for(
            job_name=self.routine_name,
            cron_expression=self.cron_expression,
        )
        self._setup(startup_script)

        agent_options = runtime_config.build_agent_options()
        runtime_prompt = (
            runtime_config.prompt_text.strip()
        )

        agent = ClaudeAgent(options=agent_options)
        await agent.run(prompt=runtime_prompt)
        print(f"routine finita[{self.routine_name}]")
