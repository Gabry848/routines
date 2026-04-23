import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pathlib import Path
from zoneinfo import ZoneInfo

from .constants import ROUTINES_PATH
from .loader import load_jobs
from .routine import Routine


@dataclass
class ExecutionRecord:
    execution_id: str
    routine_name: str
    task_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"  # running | success | failed


@dataclass
class ErrorRecord:
    routine_name: str
    task_id: str
    error_type: str
    message: str
    timestamp: datetime


class RoutineScheduler:
    def __init__(
        self,
        jobs: list[Routine],
        base_path: Path = ROUTINES_PATH,
        reload_interval_seconds: int = 10,
    ) -> None:
        self._jobs = jobs
        self._base_path = base_path
        self._reload_interval_seconds = reload_interval_seconds
        self._scheduler = AsyncIOScheduler()
        self._job_signatures: dict[str, tuple[str, str, str, str | None]] = {}

        self.started_at: datetime = datetime.now()
        self.last_sync_at: datetime | None = None
        self._running_executions: dict[str, ExecutionRecord] = {}
        self._execution_history: list[ExecutionRecord] = []
        self._last_errors: dict[str, ErrorRecord] = {}

    def _desired_jobs(self) -> dict[str, Routine]:
        jobs = load_jobs(self._base_path)
        return {job.scheduler_job_id: job for job in jobs}

    def _schedule_job(self, job: Routine) -> None:
        timezone = ZoneInfo(job.timezone)
        trigger = CronTrigger.from_crontab(job.cron_expression, timezone=timezone)

        self._scheduler.add_job(
            self._run_tracked_job,
            trigger=trigger,
            id=job.scheduler_job_id,
            replace_existing=True,
            args=[job],
        )
        self._job_signatures[job.scheduler_job_id] = job.signature

    async def _run_tracked_job(self, job: Routine) -> None:
        execution_id = (
            f"{job.scheduler_job_id}:{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        )
        record = ExecutionRecord(
            execution_id=execution_id,
            routine_name=job.routine_dir_name,
            task_id=job.task_id,
            started_at=datetime.now(),
        )
        self._running_executions[execution_id] = record
        try:
            await job.start()
            record.status = "success"
        except Exception as exc:
            record.status = "failed"
            self._last_errors[job.routine_dir_name] = ErrorRecord(
                routine_name=job.routine_dir_name,
                task_id=job.task_id,
                error_type=type(exc).__name__,
                message=str(exc),
                timestamp=datetime.now(),
            )
            traceback.print_exc()
        finally:
            record.finished_at = datetime.now()
            self._execution_history.append(record)
            self._running_executions.pop(execution_id, None)

    def _remove_job(self, job_id: str) -> None:
        if self._scheduler.get_job(job_id) is not None:
            self._scheduler.remove_job(job_id)
        self._job_signatures.pop(job_id, None)

    def sync_jobs(self) -> tuple[int, int, int]:
        desired_jobs = self._desired_jobs()
        current_job_ids = set(self._job_signatures)
        desired_job_ids = set(desired_jobs)

        removed = 0
        added = 0
        updated = 0

        for job_id in sorted(current_job_ids - desired_job_ids):
            self._remove_job(job_id)
            removed += 1

        for job_id in sorted(desired_job_ids):
            desired_job = desired_jobs[job_id]
            current_signature = self._job_signatures.get(job_id)

            if current_signature is None:
                self._schedule_job(desired_job)
                added += 1
                continue

            if current_signature != desired_job.signature:
                self._schedule_job(desired_job)
                updated += 1

        self._jobs = list(desired_jobs.values())
        self.last_sync_at = datetime.now()
        return added, updated, removed

    async def run_forever(self) -> None:
        self._scheduler.start()
        added, updated, removed = self.sync_jobs()
        print(
            "Scheduler avviato. "
            f"Routine attive: {len(self._job_signatures)} "
            f"(aggiunte={added}, aggiornate={updated}, rimosse={removed})."
        )

        try:
            while True:
                await asyncio.sleep(self._reload_interval_seconds)
                added, updated, removed = self.sync_jobs()
                if added or updated or removed:
                    print(
                        "Scheduler sincronizzato con il filesystem. "
                        f"Routine attive: {len(self._job_signatures)} "
                        f"(aggiunte={added}, aggiornate={updated}, rimosse={removed})."
                    )
        except (KeyboardInterrupt, SystemExit):
            self._scheduler.shutdown()
