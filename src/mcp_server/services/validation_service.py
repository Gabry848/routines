from __future__ import annotations

from copy import deepcopy
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from croniter import croniter
from zoneinfo import ZoneInfo, available_timezones

from scheduler.constants import DEFAULT_MODEL, ROUTINES_PATH, PROMT_FILENAME_CANDIDATES

from ..models import ValidationResult, ScriptTestResult, PromptTestResult

VALID_MODELS = ["sonnet", "opus", "haiku"]
VALID_TOOLS = [
    "Bash", "Read", "Edit", "Write", "GlobMatch", "GrepSearch",
    "LS", "View", "FileRead", "FileWrite",
]
VALID_PLUGINS: list[str] = []
DEFAULT_TIMEZONE = "Europe/Rome"
MODEL_CONFIG_FIELDS = {
    "tools",
    "allowed_tools",
    "mcp_servers",
    "mcp_selected_tools",
    "max_turns",
    "max_budget_usd",
    "disallowed_tools",
    "model",
    "add_dirs",
    "env",
    "skills",
    "sandbox",
    "plugins",
    "thinking",
    "effort",
    "session_store",
    "load_timeout_ms",
}
DOCKER_FIELDS = {"enabled", "image", "network", "extra_volumes"}
ENVIRONMENT_FIELDS = {
    "isolated_runs",
    "keep_executions",
    "clone_repo",
    "clone_branch",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def normalize_task(
    task: dict[str, Any],
    routine_name: str,
    default_task_id: str,
) -> dict[str, Any]:
    normalized_task: dict[str, Any] = {
        "task_id": task.get("task_id")
        if isinstance(task.get("task_id"), str) and task.get("task_id")
        else default_task_id,
        "job_name": task.get("job_name")
        if isinstance(task.get("job_name"), str) and task.get("job_name")
        else routine_name,
        "enabled": task.get("enabled") if isinstance(task.get("enabled"), bool) else True,
    }

    schedule = task.get("schedule", {})
    if isinstance(schedule, dict):
        normalized_schedule: dict[str, Any] = {
            "type": schedule.get("type") if isinstance(schedule.get("type"), str) else "cron",
        }
        if "expression" in schedule:
            normalized_schedule["expression"] = schedule.get("expression")
        metadata = schedule.get("metadata")
        if isinstance(metadata, dict):
            normalized_schedule["metadata"] = deepcopy(metadata)
        normalized_task["schedule"] = normalized_schedule
    else:
        normalized_task["schedule"] = schedule

    startup_script = task.get("startup_script")
    if isinstance(startup_script, str) and startup_script:
        normalized_task["startup_script"] = startup_script

    return normalized_task


def normalize_config(config: dict[str, Any], routine_name: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    scheduler = config.get("scheduler", {})
    scheduler = scheduler if isinstance(scheduler, dict) else {}
    normalized_scheduler: dict[str, Any] = {
        "enabled": scheduler.get("enabled") if isinstance(scheduler.get("enabled"), bool) else True,
        "timezone": scheduler.get("timezone")
        if isinstance(scheduler.get("timezone"), str) and scheduler.get("timezone")
        else DEFAULT_TIMEZONE,
    }

    tasks = scheduler.get("tasks", [])
    normalized_tasks: list[dict[str, Any]] = []
    if isinstance(tasks, list):
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                normalized_tasks.append(task)
                continue
            normalized_tasks.append(
                normalize_task(task, routine_name=routine_name, default_task_id=f"task-{i}")
            )

    normalized_scheduler["tasks"] = normalized_tasks
    normalized["scheduler"] = normalized_scheduler

    raw_model_config = config.get("model_config", {})
    if isinstance(raw_model_config, dict):
        normalized_model_config: dict[str, Any] = {}
        for key in MODEL_CONFIG_FIELDS:
            if key not in raw_model_config:
                continue

            value = raw_model_config[key]
            if key in {"allowed_tools", "disallowed_tools", "add_dirs", "plugins"}:
                normalized_model_config[key] = value if isinstance(value, list) else []
                continue
            if key == "mcp_servers":
                if isinstance(value, (list, dict)):
                    normalized_model_config[key] = deepcopy(value)
                continue
            if key == "mcp_selected_tools":
                if isinstance(value, dict):
                    normalized_model_config[key] = {
                        server: tools if isinstance(tools, list) else []
                        for server, tools in value.items()
                    }
                continue
            if key == "env":
                if isinstance(value, dict):
                    normalized_model_config[key] = deepcopy(value)
                continue
            if key == "load_timeout_ms":
                if isinstance(value, int) and value > 0:
                    normalized_model_config[key] = value
                continue
            normalized_model_config[key] = deepcopy(value)

        if "model" not in normalized_model_config:
            normalized_model_config["model"] = DEFAULT_MODEL
        if "allowed_tools" not in normalized_model_config:
            normalized_model_config["allowed_tools"] = ["Bash", "Read", "Edit"]
        if "load_timeout_ms" not in normalized_model_config:
            normalized_model_config["load_timeout_ms"] = 60000

        normalized["model_config"] = normalized_model_config
    else:
        normalized["model_config"] = {
            "model": DEFAULT_MODEL,
            "allowed_tools": ["Bash", "Read", "Edit"],
            "load_timeout_ms": 60000,
        }

    docker = config.get("docker")
    if isinstance(docker, dict):
        normalized_docker = {
            key: deepcopy(value)
            for key, value in docker.items()
            if key in DOCKER_FIELDS
        }
        if normalized_docker:
            normalized["docker"] = normalized_docker

    environment = config.get("environment")
    if isinstance(environment, dict):
        normalized_environment = {
            key: deepcopy(value)
            for key, value in environment.items()
            if key in ENVIRONMENT_FIELDS
        }
        if normalized_environment:
            normalized["environment"] = normalized_environment

    return normalized


def normalize_config_update(
    existing_config: dict[str, Any],
    updates: dict[str, Any],
    routine_name: str,
) -> dict[str, Any]:
    merged = deepcopy(existing_config)
    _deep_merge(merged, updates)
    return normalize_config(merged, routine_name=routine_name)


def normalize_task_update(
    existing_task: dict[str, Any],
    updates: dict[str, Any],
    routine_name: str,
    default_task_id: str,
) -> dict[str, Any]:
    merged = deepcopy(existing_task)
    _deep_merge(merged, updates)
    return normalize_task(merged, routine_name=routine_name, default_task_id=default_task_id)


def validate_task(task: dict[str, Any], *, existing_task_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    existing_task_ids = existing_task_ids or set()

    task_id = task.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        errors.append("task.task_id must be a non-empty string")
    elif task_id in existing_task_ids:
        errors.append(f"task.task_id already exists: {task_id}")

    job_name = task.get("job_name")
    if job_name is not None and not (isinstance(job_name, str) and job_name):
        errors.append("task.job_name must be a non-empty string")

    enabled = task.get("enabled")
    if enabled is not None and not isinstance(enabled, bool):
        errors.append("task.enabled must be a boolean")

    schedule = task.get("schedule")
    if not isinstance(schedule, dict):
        errors.append("task.schedule must be an object")
        return errors

    if schedule.get("type") != "cron":
        errors.append("task.schedule.type must be 'cron'")

    expr = schedule.get("expression", "")
    if expr:
        try:
            croniter(expr)
        except ValueError as e:
            errors.append(f"task.schedule.expression invalid: {e}")
    else:
        errors.append("task.schedule.expression is required")

    return errors


def validate_config(config: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []

    scheduler = config.get("scheduler")
    if not isinstance(scheduler, dict):
        return ValidationResult(valid=False, errors=["missing or invalid 'scheduler' section"])

    if "enabled" not in scheduler:
        errors.append("scheduler.enabled is required")

    tz = scheduler.get("timezone", "UTC")
    if isinstance(tz, str) and tz not in available_timezones():
        errors.append(f"invalid timezone: {tz}")

    tasks = scheduler.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("scheduler.tasks must be an array")
    elif not tasks:
        errors.append("scheduler.tasks must contain at least one task")
    else:
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"scheduler.tasks[{i}] must be an object")
                continue
            task_id = task.get("task_id")
            if task_id is not None and not (isinstance(task_id, str) and task_id):
                errors.append(f"scheduler.tasks[{i}].task_id must be a non-empty string")
            job_name = task.get("job_name")
            if job_name is not None and not (isinstance(job_name, str) and job_name):
                errors.append(f"scheduler.tasks[{i}].job_name must be a non-empty string")
            enabled = task.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                errors.append(f"scheduler.tasks[{i}].enabled must be a boolean")
            schedule = task.get("schedule", {})
            if not isinstance(schedule, dict):
                errors.append(f"scheduler.tasks[{i}].schedule must be an object")
                continue
            if schedule.get("type") != "cron":
                errors.append(f"scheduler.tasks[{i}].schedule.type must be 'cron'")
            expr = schedule.get("expression", "")
            if expr:
                try:
                    croniter(expr)
                except ValueError as e:
                    errors.append(f"scheduler.tasks[{i}].schedule.expression invalid: {e}")
            else:
                errors.append(f"scheduler.tasks[{i}].schedule.expression is required")

    model_config = config.get("model_config")
    if isinstance(model_config, dict):
        model = model_config.get("model")
        if model and model not in VALID_MODELS:
            errors.append(f"model_config.model invalid: {model}. Valid: {VALID_MODELS}")
        load_timeout_ms = model_config.get("load_timeout_ms")
        if load_timeout_ms is not None and not (
            isinstance(load_timeout_ms, int) and load_timeout_ms > 0
        ):
            errors.append("model_config.load_timeout_ms must be a positive integer")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def preview_schedule(
    cron: str,
    timezone: str = "UTC",
    count: int = 5,
) -> list[str]:
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("UTC")
    cron_iter = croniter(cron, datetime.now(tz))
    return [cron_iter.get_next(datetime).isoformat() for _ in range(count)]


def suggest_task_id(routine_name: str, base_path: Path = ROUTINES_PATH) -> str:
    import json
    config_path = base_path / routine_name / "config.json"
    existing_ids: set[str] = set()
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            tasks = data.get("scheduler", {}).get("tasks", [])
            for t in tasks:
                if isinstance(t, dict) and t.get("task_id"):
                    existing_ids.add(t["task_id"])
        except Exception:
            pass

    i = 0
    while True:
        candidate = f"task-{i}"
        if candidate not in existing_ids:
            return candidate
        i += 1


def test_startup_script(routine_name: str, base_path: Path = ROUTINES_PATH) -> ScriptTestResult | str:
    import json
    config_path = base_path / routine_name / "config.json"
    if not config_path.exists():
        return "routine not found"

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return "invalid config.json"

    tasks = data.get("scheduler", {}).get("tasks", [])
    script_name = None
    for t in tasks:
        if isinstance(t, dict) and t.get("startup_script"):
            script_name = t["startup_script"]
            break

    if not script_name:
        return "no startup_script configured"

    script_path = base_path / routine_name / script_name
    if not script_path.exists():
        return f"startup_script not found: {script_name}"

    env_dir = base_path / routine_name / "env"
    env_dir.mkdir(exist_ok=True)

    import time
    start = time.monotonic()
    result = subprocess.run(
        str(script_path),
        shell=True,
        cwd=env_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    return ScriptTestResult(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.returncode,
        duration_ms=duration_ms,
    )


def test_prompt(routine_name: str, base_path: Path = ROUTINES_PATH) -> PromptTestResult:
    routine_dir = base_path / routine_name
    issues: list[str] = []

    for filename in PROMT_FILENAME_CANDIDATES:
        prompt_path = routine_dir / filename
        if prompt_path.exists():
            text = prompt_path.read_text(encoding="utf-8")
            if not text.strip():
                issues.append("prompt file is empty")
            return PromptTestResult(
                prompt_file=filename,
                length=len(text),
                word_count=len(text.split()),
                issues=issues,
            )

    issues.append("no prompt file found")
    return PromptTestResult(issues=issues)


def list_available_options() -> dict[str, list[str]]:
    return {
        "models": VALID_MODELS,
        "tools": VALID_TOOLS,
        "plugins": VALID_PLUGINS,
    }
