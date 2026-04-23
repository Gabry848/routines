import json
from pathlib import Path
from typing import Any

from .constants import ROUTINES_PATH
from .routine import Routine


def discover_routines(base_path: Path = ROUTINES_PATH) -> list[Path]:
    if not base_path.exists():
        return []

    return sorted(path for path in base_path.iterdir() if path.is_dir())


def _normalize_task_id(task: dict[str, Any], index: int) -> str:
    explicit_task_id = task.get("task_id")
    if isinstance(explicit_task_id, str) and explicit_task_id.strip():
        return explicit_task_id.strip()

    job_name = task.get("job_name")
    if isinstance(job_name, str) and job_name.strip():
        return f"job-{job_name.strip()}"

    return f"task-{index}"


def load_jobs(base_path: Path = ROUTINES_PATH) -> list[Routine]:
    """Discover routine directories, load their configurations, and create Routine instances for enabled tasks."""
    jobs: list[Routine] = []

    for routine_dir in discover_routines(base_path):
        config_path = routine_dir / "config.json"
        if not config_path.exists():
            continue

        try:
            with config_path.open("r", encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except json.JSONDecodeError as exc:
            print(f"Config non valido per routine '{routine_dir.name}': {exc}")
            continue

        if not isinstance(config_data, dict):
            continue

        scheduler_config = config_data.get("scheduler", {})
        if not isinstance(scheduler_config, dict):
            continue

        if not scheduler_config.get("enabled", False):
            continue

        timezone = scheduler_config.get("timezone", "UTC")
        tasks = scheduler_config.get("tasks", [])
        if not isinstance(tasks, list):
            continue

        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue

            schedule = task.get("schedule", {})
            if not isinstance(schedule, dict):
                continue

            if task.get("enabled") is False:
                continue

            if schedule.get("type") != "cron":
                continue

            expression = schedule.get("expression")
            if not expression:
                continue

            job_name = task.get("job_name") or routine_dir.name
            jobs.append(
                Routine(
                    routine_dir_name=routine_dir.name,
                    task_id=_normalize_task_id(task, index),
                    routine_name=job_name,
                    timezone=timezone,
                    cron_expression=expression,
                    startup_script=task.get("startup_script") if isinstance(task.get("startup_script"), str) and task.get("startup_script") else None,
                )
            )

    return jobs
