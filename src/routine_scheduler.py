import asyncio

from scheduler.agent import ClaudeAgent
from scheduler.app import run_scheduler
from scheduler.constants import ROUTINES_PATH
from scheduler.cron import CronExpression
from scheduler.engine import RoutineScheduler
from scheduler.loader import load_jobs
from scheduler.routine import Routine

__all__ = [
    "ROUTINES_PATH",
    "CronExpression",
    "ClaudeAgent",
    "Routine",
    "load_jobs",
    "RoutineScheduler",
    "run_scheduler",
]


if __name__ == "__main__":
    asyncio.run(run_scheduler())
