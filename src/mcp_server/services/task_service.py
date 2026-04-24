from __future__ import annotations

from pathlib import Path
from typing import Any

from .routine_service import _load_config, _save_config


def _get_tasks(name: str, base_path: Path | None = None) -> tuple[list[dict], dict] | None:
    config = _load_config(name, base_path=base_path) if base_path else _load_config(name)
    if config is None:
        return None
    scheduler = config.setdefault("scheduler", {})
    tasks = scheduler.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
    return tasks, config


def add_task(name: str, task: dict[str, Any], base_path: Path | None = None) -> dict[str, Any] | None:
    result = _get_tasks(name, base_path=base_path)
    if result is None:
        return None
    tasks, config = result

    task_id = task.get("task_id")
    if task_id:
        for existing in tasks:
            if isinstance(existing, dict) and existing.get("task_id") == task_id:
                return None

    tasks.append(task)
    config["scheduler"]["tasks"] = tasks
    (_save_config(name, config, base_path=base_path) if base_path else _save_config(name, config))
    return task


def update_task(name: str, task_id: str, updates: dict[str, Any], base_path: Path | None = None) -> dict[str, Any] | None:
    result = _get_tasks(name, base_path=base_path)
    if result is None:
        return None
    tasks, config = result

    for task in tasks:
        if isinstance(task, dict) and task.get("task_id") == task_id:
            for key, value in updates.items():
                if isinstance(value, dict) and isinstance(task.get(key), dict):
                    task[key].update(value)
                else:
                    task[key] = value
            (_save_config(name, config, base_path=base_path) if base_path else _save_config(name, config))
            return task
    return None


def replace_task(name: str, task_id: str, new_task: dict[str, Any], base_path: Path | None = None) -> dict[str, Any] | None:
    result = _get_tasks(name, base_path=base_path)
    if result is None:
        return None
    tasks, config = result

    for i, task in enumerate(tasks):
        if isinstance(task, dict) and task.get("task_id") == task_id:
            tasks[i] = new_task
            config["scheduler"]["tasks"] = tasks
            (_save_config(name, config, base_path=base_path) if base_path else _save_config(name, config))
            return new_task
    return None


def delete_task(name: str, task_id: str, base_path: Path | None = None) -> bool:
    result = _get_tasks(name, base_path=base_path)
    if result is None:
        return False
    tasks, config = result

    new_tasks = [
        t for t in tasks
        if not (isinstance(t, dict) and t.get("task_id") == task_id)
    ]
    if len(new_tasks) == len(tasks):
        return False

    config["scheduler"]["tasks"] = new_tasks
    if not new_tasks:
        config["scheduler"]["enabled"] = False
    (_save_config(name, config, base_path=base_path) if base_path else _save_config(name, config))
    return True


def set_task_enabled(name: str, task_id: str, enabled: bool, base_path: Path | None = None) -> bool:
    result = _get_tasks(name, base_path=base_path)
    if result is None:
        return False
    tasks, config = result

    for task in tasks:
        if isinstance(task, dict) and task.get("task_id") == task_id:
            task["enabled"] = enabled
            (_save_config(name, config, base_path=base_path) if base_path else _save_config(name, config))
            return True
    return False
