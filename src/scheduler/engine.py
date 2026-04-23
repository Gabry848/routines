import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pathlib import Path
from zoneinfo import ZoneInfo

from .constants import ROUTINES_PATH
from .loader import load_jobs
from .routine import Routine


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

    def _desired_jobs(self) -> dict[str, Routine]:
        jobs = load_jobs(self._base_path)
        return {job.scheduler_job_id: job for job in jobs}

    def _schedule_job(self, job: Routine) -> None:
        timezone = ZoneInfo(job.timezone)
        trigger = CronTrigger.from_crontab(job.cron_expression, timezone=timezone)

        self._scheduler.add_job(
            job.start,
            trigger=trigger,
            id=job.scheduler_job_id,
            replace_existing=True,
        )
        self._job_signatures[job.scheduler_job_id] = job.signature

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
