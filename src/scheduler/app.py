from pathlib import Path

from .constants import ROUTINES_PATH
from .engine import RoutineScheduler
from .loader import load_jobs


async def run_scheduler(base_path: Path = ROUTINES_PATH) -> None:
    jobs = load_jobs(base_path)
    scheduler = RoutineScheduler(jobs)
    await scheduler.run_forever()
