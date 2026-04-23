import json
import tempfile
import unittest
from pathlib import Path

from scheduler.engine import RoutineScheduler
from scheduler.loader import load_jobs


class SchedulerSyncTests(unittest.TestCase):
    def test_load_jobs_skips_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            routine_dir = base_path / "broken"
            routine_dir.mkdir()
            (routine_dir / "config.json").write_text("{ invalid", encoding="utf-8")

            jobs = load_jobs(base_path)

            self.assertEqual(jobs, [])


class SchedulerSyncAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_jobs_handles_add_update_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            routine_dir = base_path / "example"
            routine_dir.mkdir()
            self._write_config(
                routine_dir,
                enabled=True,
                timezone="Europe/Rome",
                tasks=[
                    {
                        "task_id": "daily",
                        "job_name": "example-cron-job",
                        "schedule": {"type": "cron", "expression": "30 9 * * *"},
                    }
                ],
            )

            scheduler = RoutineScheduler(load_jobs(base_path), base_path=base_path)
            scheduler._scheduler.start(paused=True)
            self.addAsyncCleanup(self._shutdown_scheduler, scheduler)

            added, updated, removed = scheduler.sync_jobs()
            self.assertEqual((added, updated, removed), (1, 0, 0))

            job = scheduler._scheduler.get_job("example:daily")
            self.assertIsNotNone(job)
            self.assertEqual(str(job.trigger), "cron[month='*', day='*', day_of_week='*', hour='9', minute='30']")

            self._write_config(
                routine_dir,
                enabled=True,
                timezone="Europe/Rome",
                tasks=[
                    {
                        "task_id": "daily",
                        "job_name": "example-cron-job-renamed",
                        "schedule": {"type": "cron", "expression": "45 10 * * *"},
                        "startup_script": "setup.sh",
                    }
                ],
            )

            added, updated, removed = scheduler.sync_jobs()
            self.assertEqual((added, updated, removed), (0, 1, 0))

            updated_job = scheduler._scheduler.get_job("example:daily")
            self.assertIsNotNone(updated_job)
            self.assertEqual(str(updated_job.trigger), "cron[month='*', day='*', day_of_week='*', hour='10', minute='45']")

            self._write_config(routine_dir, enabled=False, timezone="Europe/Rome", tasks=[])

            added, updated, removed = scheduler.sync_jobs()
            self.assertEqual((added, updated, removed), (0, 0, 1))
            self.assertIsNone(scheduler._scheduler.get_job("example:daily"))

    def _write_config(
        self,
        routine_dir: Path,
        *,
        enabled: bool,
        timezone: str,
        tasks: list[dict],
    ) -> None:
        payload = {
            "scheduler": {
                "enabled": enabled,
                "timezone": timezone,
                "tasks": tasks,
            }
        }
        (routine_dir / "config.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    async def _shutdown_scheduler(self, scheduler: RoutineScheduler) -> None:
        scheduler._scheduler.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
