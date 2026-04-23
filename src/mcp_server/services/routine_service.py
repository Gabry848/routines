from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from croniter import croniter
from scheduler.constants import ROUTINES_PATH, PROMT_FILENAME_CANDIDATES
from scheduler.loader import discover_routines

from ..models import RoutineSummary, RoutineDetail, TaskSummary, ExportPayload


def _routine_dir(name: str, base_path: Path = ROUTINES_PATH) -> Path:
    return base_path / name


def _load_config(name: str, base_path: Path = ROUTINES_PATH) -> dict[str, Any] | None:
    config_path = _routine_dir(name, base_path) / "config.json"
    if not config_path.exists():
        return None
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def _save_config(name: str, config: dict[str, Any], base_path: Path = ROUTINES_PATH) -> None:
    routine_dir = _routine_dir(name, base_path)
    routine_dir.mkdir(parents=True, exist_ok=True)
    config_path = routine_dir / "config.json"
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _load_prompt(name: str, base_path: Path = ROUTINES_PATH) -> tuple[str, str | None]:
    routine_dir = _routine_dir(name, base_path)
    for filename in PROMT_FILENAME_CANDIDATES:
        prompt_path = routine_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8"), filename
    return "", None


def _build_task_summaries(config: dict[str, Any]) -> list[TaskSummary]:
    scheduler_config = config.get("scheduler", {})
    if not isinstance(scheduler_config, dict):
        return []
    timezone = scheduler_config.get("timezone", "UTC")
    tasks_raw = scheduler_config.get("tasks", [])
    if not isinstance(tasks_raw, list):
        return []

    summaries = []
    for i, task in enumerate(tasks_raw):
        if not isinstance(task, dict):
            continue
        schedule = task.get("schedule", {})
        cron_expr = schedule.get("expression", "") if isinstance(schedule, dict) else ""
        task_id = task.get("task_id") or task.get("job_name") or f"task-{i}"

        next_run = None
        if cron_expr:
            try:
                tz_name = timezone
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(tz_name)
                cron = croniter(cron_expr, datetime.now(tz))
                next_run = cron.get_next(datetime).isoformat()
            except Exception:
                pass

        summaries.append(TaskSummary(
            task_id=task_id,
            job_name=task.get("job_name"),
            cron=cron_expr,
            timezone=timezone,
            enabled=task.get("enabled", True),
            next_run=next_run,
        ))
    return summaries


def list_routines(base_path: Path = ROUTINES_PATH) -> list[RoutineSummary]:
    results = []
    for routine_dir in discover_routines(base_path):
        config = _load_config(routine_dir.name, base_path)
        if config is None:
            continue
        scheduler_config = config.get("scheduler", {})
        enabled = scheduler_config.get("enabled", False) if isinstance(scheduler_config, dict) else False
        tasks = _build_task_summaries(config)
        results.append(RoutineSummary(
            name=routine_dir.name,
            enabled=enabled,
            path=str(routine_dir),
            tasks=tasks,
        ))
    return results


def get_routine(name: str, task_id: str | None = None, base_path: Path = ROUTINES_PATH) -> RoutineDetail | None:
    config = _load_config(name, base_path)
    if config is None:
        return None
    routine_dir = _routine_dir(name, base_path)
    scheduler_config = config.get("scheduler", {})
    enabled = scheduler_config.get("enabled", False) if isinstance(scheduler_config, dict) else False
    prompt_text, _ = _load_prompt(name, base_path)
    tasks = _build_task_summaries(config)

    if task_id:
        tasks = [t for t in tasks if t.task_id == task_id]

    return RoutineDetail(
        name=name,
        enabled=enabled,
        path=str(routine_dir),
        config=config,
        prompt_text=prompt_text,
        tasks=tasks,
    )


def create_routine(name: str, config: dict[str, Any], prompt: str, base_path: Path = ROUTINES_PATH) -> RoutineDetail | None:
    routine_dir = _routine_dir(name, base_path)
    if routine_dir.exists():
        return None
    routine_dir.mkdir(parents=True, exist_ok=True)
    (routine_dir / "env").mkdir(exist_ok=True)
    _save_config(name, config, base_path)
    (routine_dir / "PROMPT.md").write_text(prompt, encoding="utf-8")
    return get_routine(name, base_path=base_path)


def update_routine_config(name: str, updates: dict[str, Any], base_path: Path = ROUTINES_PATH) -> dict[str, Any] | None:
    config = _load_config(name, base_path)
    if config is None:
        return None
    _deep_merge(config, updates)
    _save_config(name, config, base_path)
    return config


def delete_routine(name: str, mode: str = "disable", base_path: Path = ROUTINES_PATH) -> bool:
    routine_dir = _routine_dir(name, base_path)
    if not routine_dir.exists():
        return False
    if mode == "delete":
        shutil.rmtree(routine_dir)
    else:
        config = _load_config(name, base_path)
        if config:
            scheduler = config.setdefault("scheduler", {})
            scheduler["enabled"] = False
            _save_config(name, config, base_path)
    return True


def rename_routine(old_name: str, new_name: str, base_path: Path = ROUTINES_PATH) -> RoutineDetail | None:
    old_dir = _routine_dir(old_name, base_path)
    new_dir = _routine_dir(new_name, base_path)
    if not old_dir.exists() or new_dir.exists():
        return None
    old_dir.rename(new_dir)
    return get_routine(new_name, base_path=base_path)


def clone_routine(name: str, new_name: str, base_path: Path = ROUTINES_PATH) -> RoutineDetail | None:
    src_dir = _routine_dir(name, base_path)
    dst_dir = _routine_dir(new_name, base_path)
    if not src_dir.exists() or dst_dir.exists():
        return None
    shutil.copytree(src_dir, dst_dir)

    config = _load_config(new_name, base_path)
    if config:
        tasks = config.get("scheduler", {}).get("tasks", [])
        for i, task in enumerate(tasks):
            if isinstance(task, dict):
                task["task_id"] = f"{task.get('task_id', f'task-{i}')}-copy"
        _save_config(new_name, config, base_path)

    return get_routine(new_name, base_path=base_path)


def set_routine_enabled(name: str, enabled: bool, base_path: Path = ROUTINES_PATH) -> bool:
    config = _load_config(name, base_path)
    if config is None:
        return False
    scheduler = config.setdefault("scheduler", {})
    scheduler["enabled"] = enabled
    _save_config(name, config, base_path)
    return True


def export_routine(name: str, base_path: Path = ROUTINES_PATH) -> ExportPayload | None:
    config = _load_config(name, base_path)
    if config is None:
        return None
    routine_dir = _routine_dir(name, base_path)
    prompt_text, _ = _load_prompt(name, base_path)
    files = [str(p.relative_to(routine_dir)) for p in routine_dir.rglob("*") if p.is_file()]
    return ExportPayload(name=name, config=config, prompt_text=prompt_text, files=files)


def import_routine(name: str, config: dict[str, Any], prompt: str, base_path: Path = ROUTINES_PATH) -> RoutineDetail | None:
    return create_routine(name, config, prompt, base_path)


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
