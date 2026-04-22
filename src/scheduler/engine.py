import asyncio
import heapq
from datetime import datetime
from zoneinfo import ZoneInfo

from .cron import CronExpression
from .routine import Routine


class RoutineScheduler:
    def __init__(self, jobs: list[Routine]) -> None:
        self._jobs = jobs
        self._queue: list[tuple[datetime, int, Routine, CronExpression, ZoneInfo]] = []
        self._counter = 0
        self._running_tasks: set[asyncio.Task[None]] = set()

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        self._running_tasks.discard(task)
        try:
            task.result()
        except Exception as exc:
            print(f"routine error: {exc}")

    def _build_queue(self) -> None:
        self._queue.clear()

        for job in self._jobs:
            timezone = ZoneInfo(job.timezone)
            cron = CronExpression(job.cron_expression)
            now = datetime.now(timezone)
            next_run = cron.next_run_after(now)
            heapq.heappush(self._queue, (next_run, self._counter, job, cron, timezone))
            self._counter += 1

        print(f"Scheduler avviato con {len(self._queue)} routine schedulate.")

    async def run_forever(self) -> None:
        if not self._jobs:
            print("Nessuna routine schedulata trovata.")
            return

        self._build_queue()

        while self._queue:
            next_run, _, job, cron, timezone = heapq.heappop(self._queue)
            now = datetime.now(timezone)
            delay_seconds = (next_run - now).total_seconds()

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            task = asyncio.create_task(job.start())
            self._running_tasks.add(task)
            task.add_done_callback(self._on_task_done)

            now = datetime.now(timezone)
            following_run = cron.next_run_after(now)
            heapq.heappush(self._queue, (following_run, self._counter, job, cron, timezone))
            self._counter += 1
