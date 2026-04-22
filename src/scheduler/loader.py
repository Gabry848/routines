import json
from pathlib import Path

from .constants import ROUTINES_PATH
from .routine import Routine


def discover_routines(base_path: Path = ROUTINES_PATH) -> list[Path]:
    if not base_path.exists():
        return []

    return sorted(path for path in base_path.iterdir() if path.is_dir())


def load_jobs(base_path: Path = ROUTINES_PATH) -> list[Routine]:
    """Discover routine directories, load their configurations, and create Routine instances for enabled tasks."""
    jobs: list[Routine] = []

    for routine_dir in discover_routines(base_path):
        config_path = routine_dir / "config.json"
        if not config_path.exists():
            continue

        with config_path.open("r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)

        scheduler_config = config_data.get("scheduler", {})
        if not scheduler_config.get("enabled", False):
            continue

        timezone = scheduler_config.get("timezone", "UTC")
        tasks = scheduler_config.get("tasks", [])

        for task in tasks:
            schedule = task.get("schedule", {})
            if schedule.get("type") != "cron":
                continue

            expression = schedule.get("expression")
            if not expression:
                continue

            job_name = task.get("job_name") or routine_dir.name
            jobs.append(
                Routine(
                    routine_dir_name=routine_dir.name,
                    routine_name=job_name,
                    timezone=timezone,
                    cron_expression=expression,
                )
            )

    return jobs
