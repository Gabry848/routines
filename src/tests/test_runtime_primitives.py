"""Tests for runtime primitives: task.enabled filter, execution tracking, heartbeat, history, errors."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from scheduler.loader import load_jobs
from scheduler.engine import RoutineScheduler


@pytest.fixture
def routine_dir(tmp_path):
    """Create a minimal routine directory with config.json."""
    rdir = tmp_path / "test-routine"
    rdir.mkdir()
    (rdir / "PROMPT.md").write_text("test prompt")
    (rdir / "env").mkdir()
    return rdir


def _write_config(routine_dir: Path, tasks: list[dict], enabled: bool = True):
    config = {
        "scheduler": {
            "enabled": enabled,
            "timezone": "UTC",
            "tasks": tasks,
        },
        "model_config": {"model": "sonnet"},
    }
    (routine_dir / "config.json").write_text(json.dumps(config))


class TestTaskEnabledFilter:
    def test_enabled_task_loaded(self, routine_dir, tmp_path):
        _write_config(routine_dir, [
            {"task_id": "t1", "schedule": {"type": "cron", "expression": "0 9 * * *"}},
        ])
        jobs = load_jobs(tmp_path)
        assert len(jobs) == 1
        assert jobs[0].task_id == "t1"

    def test_disabled_task_skipped(self, routine_dir, tmp_path):
        _write_config(routine_dir, [
            {"task_id": "t1", "enabled": True, "schedule": {"type": "cron", "expression": "0 9 * * *"}},
            {"task_id": "t2", "enabled": False, "schedule": {"type": "cron", "expression": "0 10 * * *"}},
        ])
        jobs = load_jobs(tmp_path)
        assert len(jobs) == 1
        assert jobs[0].task_id == "t1"

    def test_no_enabled_field_defaults_true(self, routine_dir, tmp_path):
        _write_config(routine_dir, [
            {"task_id": "t1", "schedule": {"type": "cron", "expression": "0 9 * * *"}},
        ])
        jobs = load_jobs(tmp_path)
        assert len(jobs) == 1

    def test_all_disabled_yields_empty(self, routine_dir, tmp_path):
        _write_config(routine_dir, [
            {"task_id": "t1", "enabled": False, "schedule": {"type": "cron", "expression": "0 9 * * *"}},
            {"task_id": "t2", "enabled": False, "schedule": {"type": "cron", "expression": "0 10 * * *"}},
        ])
        jobs = load_jobs(tmp_path)
        assert len(jobs) == 0


class TestExecutionTracking:
    def test_scheduler_has_tracking_attrs(self):
        scheduler = RoutineScheduler([], base_path=Path("/tmp"))
        assert hasattr(scheduler, "_running_executions")
        assert hasattr(scheduler, "_execution_history")
        assert hasattr(scheduler, "_last_errors")
        assert isinstance(scheduler._running_executions, dict)
        assert isinstance(scheduler._execution_history, list)
        assert isinstance(scheduler._last_errors, dict)

    def test_heartbeat_on_init(self):
        scheduler = RoutineScheduler([], base_path=Path("/tmp"))
        assert scheduler.started_at is not None
        assert isinstance(scheduler.started_at, datetime)

    def test_last_sync_updated_on_sync(self, routine_dir, tmp_path):
        _write_config(routine_dir, [
            {"task_id": "t1", "schedule": {"type": "cron", "expression": "0 9 * * *"}},
        ])
        scheduler = RoutineScheduler([], base_path=tmp_path)
        assert scheduler.last_sync_at is None
        scheduler.sync_jobs()
        assert scheduler.last_sync_at is not None
        assert isinstance(scheduler.last_sync_at, datetime)

    def test_empty_history_initially(self):
        scheduler = RoutineScheduler([], base_path=Path("/tmp"))
        assert len(scheduler._execution_history) == 0
        assert len(scheduler._running_executions) == 0
        assert len(scheduler._last_errors) == 0
