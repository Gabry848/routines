from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from scheduler.loader import load_jobs, discover_routines

from ..models import (
    SchedulerStatus,
    ExecutionInfo,
    DriftResult,
)

if TYPE_CHECKING:
    from scheduler.engine import RoutineScheduler


def get_status(scheduler: RoutineScheduler) -> SchedulerStatus:
    all_routines = [
        d.name for d in discover_routines(scheduler._base_path)
    ]
    enabled_configs = 0
    import json
    for name in all_routines:
        config_path = scheduler._base_path / name / "config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                if data.get("scheduler", {}).get("enabled"):
                    enabled_configs += 1
            except Exception:
                pass

    return SchedulerStatus(
        status="running",
        started_at=scheduler.started_at.isoformat() if scheduler.started_at else None,
        last_sync_at=scheduler.last_sync_at.isoformat() if scheduler.last_sync_at else None,
        polling_interval_seconds=scheduler._reload_interval_seconds,
        active_job_count=len(scheduler._job_signatures),
        total_routines=len(all_routines),
        enabled_routines=enabled_configs,
    )


def reload_routines(scheduler: RoutineScheduler) -> tuple[int, int, int]:
    return scheduler.sync_jobs()


def run_routine_now(scheduler: RoutineScheduler, name: str, task_id: str | None = None) -> str | None:
    jobs = load_jobs(scheduler._base_path)
    matching = [
        j for j in jobs
        if j.routine_dir_name == name and (task_id is None or j.task_id == task_id)
    ]
    if not matching:
        return None
    for job in matching:
        scheduler._scheduler.add_job(
            scheduler._run_tracked_job,
            args=[job],
            id=f"manual-{job.scheduler_job_id}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        )
    return f"triggered {len(matching)} task(s)"


def list_running_executions(scheduler: RoutineScheduler) -> list[ExecutionInfo]:
    results = []
    now = datetime.now()
    for record in scheduler._running_executions.values():
        duration = (now - record.started_at).total_seconds() if record.started_at else None
        results.append(ExecutionInfo(
            execution_id=record.execution_id,
            routine_name=record.routine_name,
            task_id=record.task_id,
            started_at=record.started_at.isoformat(),
            status=record.status,
            duration_seconds=duration,
        ))
    return results


def check_filesystem_drift(scheduler: RoutineScheduler) -> DriftResult:
    desired = {j.scheduler_job_id for j in load_jobs(scheduler._base_path)}
    current = set(scheduler._job_signatures.keys())

    in_memory_only = sorted(current - desired)
    on_disk_only = sorted(desired - current)

    config_changed = []
    for job_id in current & desired:
        sig_in_memory = scheduler._job_signatures.get(job_id)
        for job in load_jobs(scheduler._base_path):
            if job.scheduler_job_id == job_id and job.signature != sig_in_memory:
                config_changed.append(job_id)
                break

    return DriftResult(
        in_memory_only=in_memory_only,
        on_disk_only=on_disk_only,
        config_changed=config_changed,
    )


def get_execution_history(scheduler: RoutineScheduler, name: str | None = None, limit: int = 20) -> list[ExecutionInfo]:
    records = scheduler._execution_history
    if name:
        records = [r for r in records if r.routine_name == name]
    records = records[-limit:]

    results = []
    for record in reversed(records):
        duration = None
        if record.finished_at and record.started_at:
            duration = (record.finished_at - record.started_at).total_seconds()
        results.append(ExecutionInfo(
            execution_id=record.execution_id,
            routine_name=record.routine_name,
            task_id=record.task_id,
            started_at=record.started_at.isoformat(),
            finished_at=record.finished_at.isoformat() if record.finished_at else None,
            status=record.status,
            duration_seconds=duration,
        ))
    return results
