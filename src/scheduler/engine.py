import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from .routine import Routine


class RoutineScheduler:
    def __init__(self, jobs: list[Routine]) -> None:
        self._jobs = jobs
        self._scheduler = AsyncIOScheduler()

    async def run_forever(self) -> None:
        if not self._jobs:
            print("Nessuna routine schedulata trovata.")
            return

        for job in self._jobs:
            timezone = ZoneInfo(job.timezone)
            trigger = CronTrigger.from_crontab(job.cron_expression, timezone=timezone)
            
            self._scheduler.add_job(
                job.start,
                trigger=trigger,
                id=f"{job.routine_dir_name}_{job.routine_name}",
                replace_existing=True
            )

        print(f"Scheduler avviato con {len(self._jobs)} routine schedulate via APScheduler.")
        self._scheduler.start()

        try:
            # Mantiene in vita il loop principale finché lo scheduler gira
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            self._scheduler.shutdown()
