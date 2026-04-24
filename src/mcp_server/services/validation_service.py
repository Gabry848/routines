from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from croniter import croniter
from zoneinfo import ZoneInfo, available_timezones

from scheduler.constants import ROUTINES_PATH, PROMT_FILENAME_CANDIDATES

from ..models import ValidationResult, ScriptTestResult, PromptTestResult

VALID_MODELS = ["sonnet", "opus", "haiku"]
VALID_TOOLS = [
    "Bash", "Read", "Edit", "Write", "GlobMatch", "GrepSearch",
    "LS", "View", "FileRead", "FileWrite",
]
VALID_PLUGINS: list[str] = []


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
    else:
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"scheduler.tasks[{i}] must be an object")
                continue
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
