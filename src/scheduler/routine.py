import json
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from .agent import ClaudeAgent
from .constants import (
    DEFAULT_MODEL,
    DEFAULT_TOOLS,
    LOCAL_CLAUDE_JSON_PATH,
    PROJECT_ROOT,
    PROMT_FILENAME_CANDIDATES,
    ROUTINES_PATH,
)
from .mcp_config import resolve_server_names
from .project_config import build_runtime_settings, ensure_local_config_dirs


class RoutineConfig:
    MODEL_CONFIG_DEFAULTS: dict[str, Any] = {
        "tools": None,
        "allowed_tools": [],
        "mcp_servers": [],
        "mcp_selected_tools": {},
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

            if key == "mcp_servers":
                if isinstance(value, list):
                    sanitized[key] = value
                elif isinstance(value, dict):
                    sanitized[key] = value
                else:
                    sanitized[key] = []
                continue

            if key == "mcp_selected_tools":
                if isinstance(value, dict):
                    sanitized[key] = {
                        k: v if isinstance(v, list) else []
                        for k, v in value.items()
                    }
                else:
                    sanitized[key] = {}
                continue

            if key == "env":
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

        # Abilito sempre la SanBox per sicurezza in modo tale che claude nn possa uscire dalla sua cartella
        # sovrascrivo il valore attuale 
        sanitized["sandbox"] = True

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

    def build_agent_options(self, target_dir: Path) -> ClaudeAgentOptions:
        options_payload = dict(self.model_config)

        options_payload["cwd"] = target_dir
        options_payload["model"] = options_payload.get("model") or DEFAULT_MODEL

        # --- MCP Server Resolution ---
        mcp_servers_raw = options_payload.pop("mcp_servers", [])
        mcp_selected_tools = options_payload.pop("mcp_selected_tools", {})

        resolved_mcp: dict[str, Any] = {}
        if isinstance(mcp_servers_raw, list) and mcp_servers_raw:
            project_root = self.routine_path.parent.parent
            try:
                resolved_mcp = resolve_server_names(mcp_servers_raw, project_root=project_root)
            except ValueError as e:
                print(f"WARNING: {e}")
                resolved_mcp = {}
        elif isinstance(mcp_servers_raw, dict) and mcp_servers_raw:
            resolved_mcp = mcp_servers_raw

        if resolved_mcp:
            options_payload["mcp_servers"] = resolved_mcp

        # --- Build allowed_tools ---
        base_tools = options_payload.pop("allowed_tools", None) or []
        auto_mcp_tools: list[str] = []
        for server_name in resolved_mcp:
            namespace = server_name.replace("-", "_")
            tool_names = mcp_selected_tools.get(server_name, [])
            if tool_names:
                for tool_name in tool_names:
                    auto_mcp_tools.append(f"mcp__{namespace}__{tool_name}")
            else:
                auto_mcp_tools.append(f"mcp__{namespace}__")

        all_tools = list(dict.fromkeys(base_tools + auto_mcp_tools))
        options_payload["allowed_tools"] = all_tools or DEFAULT_TOOLS
        options_payload["permission_mode"] = (
            options_payload.get("permission_mode") or "bypassPermissions"
        )
        extra_args = options_payload.get("extra_args")
        if not isinstance(extra_args, dict):
            extra_args = {}
        extra_args.setdefault("allow-dangerously-skip-permissions", None)
        options_payload["extra_args"] = extra_args
        if options_payload.get("sandbox") is None:
            options_payload["sandbox"] = True
            
        if options_payload.get("sandbox"):
            options_payload["load_timeout_ms"] = max(options_payload.get("load_timeout_ms", 60000), 300000)

        docker_config = self.config_data.get("docker", {})
        if docker_config.get("enabled"):
            image = docker_config.get("image", "node:20")
            network = docker_config.get("network", "bridge")
            extra_volumes = docker_config.get("extra_volumes", [])
            ensure_local_config_dirs()
            
            runtime_dir = PROJECT_ROOT / ".runtime" / "scheduler" / self.routine_dir_name
            runtime_dir.mkdir(parents=True, exist_ok=True)
            wrapper_path = runtime_dir / "docker_wrapper.sh"
            
            volumes_args = []
            for vol in extra_volumes:
                volumes_args.append(f"-v {vol}")
            
            # Genera un settings.json runtime minimale con solo auth/config strettamente
            # necessarie al container, senza ereditare permissions o altri default globali.
            filtered_settings_path = runtime_dir / "docker_settings.json"
            settings_data = build_runtime_settings(project_root=PROJECT_ROOT)
            self._merge_auto_permissions(settings_data, options_payload["allowed_tools"])
            with filtered_settings_path.open("w", encoding="utf-8") as sf:
                json.dump(settings_data, sf, indent=2)

            container_home_dir = runtime_dir / "docker_home"
            container_claude_dir = container_home_dir / ".claude"
            container_claude_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LOCAL_CLAUDE_JSON_PATH, container_home_dir / ".claude.json")
            shutil.copy2(filtered_settings_path, container_claude_dir / "settings.json")

            script_content = f"""#!/bin/bash
# Wrapper globale per eseguire l'agent in Docker
echo ">>> [Docker Wrapper] Esecuzione in container con network=$CLAUDE_DOCKER_NETWORK image=$CLAUDE_DOCKER_IMAGE" >&2

exec docker run -i --rm \\
  --network "$CLAUDE_DOCKER_NETWORK" \\
  --user "$(id -u):$(id -g)" \\
  -e HOME=/tmp/claude-home \\
  -e npm_config_cache=/tmp/claude-home/.npm \\
  -v "$PWD:/env" \\
  -v "{container_home_dir}:/tmp/claude-home" \\
  $CLAUDE_DOCKER_VOLUMES \\
  -w /env \\
  "$CLAUDE_DOCKER_IMAGE" npx -y @anthropic-ai/claude-code@latest "$@"
"""
            wrapper_path.write_text(script_content)
            wrapper_path.chmod(0o755)
            
            options_payload["cli_path"] = str(wrapper_path)

            add_dirs = options_payload.get("add_dirs") or []
            add_dirs = [str(path) for path in add_dirs]
            if "/tmp/claude-home" not in add_dirs:
                add_dirs.append("/tmp/claude-home")
            options_payload["add_dirs"] = add_dirs
            
            # Passiamo le opzioni variabili al wrapper iniettandole nell'env del thread locale Python
            custom_env = options_payload.get("env") or {}
            custom_env["CLAUDE_DOCKER_NETWORK"] = network
            custom_env["CLAUDE_DOCKER_IMAGE"] = image
            custom_env["CLAUDE_DOCKER_VOLUMES"] = " ".join(volumes_args)
            options_payload["env"] = custom_env

        return ClaudeAgentOptions(**options_payload)

    @staticmethod
    def _merge_auto_permissions(settings_data: dict[str, Any], allowed_tools: list[str]) -> None:
        permissions = settings_data.get("permissions")
        if not isinstance(permissions, dict):
            permissions = {}
            settings_data["permissions"] = permissions

        for tool_name in allowed_tools:
            if not isinstance(tool_name, str) or not tool_name:
                continue
            current = permissions.get(tool_name)
            if isinstance(current, dict):
                current.setdefault("mode", "auto")
                continue
            permissions[tool_name] = {"mode": "auto"}


class Routine:
    def __init__(
        self,
        routine_dir_name: str,
        task_id: str,
        routine_name: str,
        timezone: str,
        cron_expression: str,
        startup_script: str | None = None,
    ) -> None:
        self.routine_dir_name = routine_dir_name
        self.task_id = task_id
        self.routine_name = routine_name
        self.timezone = timezone
        self.cron_expression = cron_expression
        self.startup_script = startup_script

    @property
    def scheduler_job_id(self) -> str:
        return f"{self.routine_dir_name}:{self.task_id}"

    @property
    def signature(self) -> tuple[str, str, str, str | None]:
        return (
            self.routine_name,
            self.timezone,
            self.cron_expression,
            self.startup_script,
        )

    def _setup(self, startup_script: str | None, target_dir: Path) -> None:
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
            cwd=target_dir,
            check=False,
        )

    async def start(self) -> None:
        """Logic to execute when the routine is triggered."""
        print(f"routine partita[{self.routine_name}]")

        runtime_config = RoutineConfig(self.routine_dir_name).load()
        env_config = runtime_config.config_data.get("environment", {})
        
        isolated_runs = env_config.get("isolated_runs", False)
        clone_repo = env_config.get("clone_repo")
        clone_branch = env_config.get("clone_branch", "main")
        keep_executions = env_config.get("keep_executions", False)

        routine_base_path = ROUTINES_PATH / self.routine_dir_name
        base_env_path = routine_base_path / "env"
        
        if isolated_runs:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            target_dir = routine_base_path / "envs" / timestamp
            target_dir.mkdir(parents=True, exist_ok=True)
            
            if clone_repo:
                clone_cmd = ["git", "clone", "-b", clone_branch, clone_repo, "."]
                print(f"Clonando repo: {' '.join(clone_cmd)} in {target_dir}...")
                subprocess.run(clone_cmd, cwd=target_dir, check=True)
                # Fix permessi per Docker: rendi scrivibile da tutti gli utenti
                chmod_cmd = ["chmod", "-R", "a+w", "."]
                subprocess.run(chmod_cmd, cwd=target_dir, check=True)
            elif base_env_path.exists():
                shutil.copytree(base_env_path, target_dir, dirs_exist_ok=True)
        else:
            target_dir = base_env_path
            target_dir.mkdir(parents=True, exist_ok=True)
            if clone_repo and not any(target_dir.iterdir()):
                clone_cmd = ["git", "clone", "-b", clone_branch, clone_repo, "."]
                print(f"Clonando repo iniziale: {' '.join(clone_cmd)} in {target_dir}...")
                subprocess.run(clone_cmd, cwd=target_dir, check=True)
                # Fix permessi per Docker: rendi scrivibile da tutti gli utenti
                chmod_cmd = ["chmod", "-R", "a+w", "."]
                subprocess.run(chmod_cmd, cwd=target_dir, check=True)

        self._setup(self.startup_script, target_dir)

        agent_options = runtime_config.build_agent_options(target_dir)
        runtime_prompt = runtime_config.prompt_text.strip()

        agent = ClaudeAgent(options=agent_options)
        try:
            await agent.run(prompt=runtime_prompt)
        finally:
            if isolated_runs and not keep_executions:
                print(f"Rimuovo esecuzione effimera: {target_dir}")
                shutil.rmtree(target_dir, ignore_errors=True)

        print(f"routine finita[{self.routine_name}]")
