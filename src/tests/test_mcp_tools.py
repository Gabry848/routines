"""Tests for MCP tool functions with mock scheduler."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server.services import routine_service, task_service, validation_service


@pytest.fixture
def routine_dir(tmp_path):
    rdir = tmp_path / "test-routine"
    rdir.mkdir()
    (rdir / "PROMPT.md").write_text("test prompt content")
    (rdir / "env").mkdir()
    config = {
        "scheduler": {
            "enabled": True,
            "timezone": "UTC",
            "tasks": [
                {"task_id": "task-0", "schedule": {"type": "cron", "expression": "0 9 * * *"}},
            ],
        },
        "model_config": {"model": "sonnet"},
    }
    (rdir / "config.json").write_text(json.dumps(config))
    return rdir


class TestRoutineTools:
    def test_list_routines(self, routine_dir, tmp_path):
        routines = routine_service.list_routines(tmp_path)
        assert len(routines) == 1
        assert routines[0].name == "test-routine"
        assert routines[0].enabled is True

    def test_get_routine(self, routine_dir, tmp_path):
        detail = routine_service.get_routine("test-routine", base_path=tmp_path)
        assert detail is not None
        assert detail.name == "test-routine"
        assert detail.prompt_text == "test prompt content"

    def test_get_routine_not_found(self, tmp_path):
        detail = routine_service.get_routine("nonexistent", base_path=tmp_path)
        assert detail is None

    def test_create_routine(self, tmp_path):
        config = {"scheduler": {"enabled": True, "timezone": "UTC", "tasks": []}, "model_config": {}}
        result = routine_service.create_routine("new-routine", config, "hello", tmp_path)
        assert result is not None
        assert result.name == "new-routine"
        assert (tmp_path / "new-routine" / "config.json").exists()
        assert (tmp_path / "new-routine" / "PROMPT.md").exists()

    def test_create_routine_duplicate(self, routine_dir, tmp_path):
        config = {"scheduler": {"enabled": True, "timezone": "UTC", "tasks": []}, "model_config": {}}
        result = routine_service.create_routine("test-routine", config, "hello", tmp_path)
        assert result is None

    def test_delete_routine_soft(self, routine_dir, tmp_path):
        success = routine_service.delete_routine("test-routine", mode="disable", base_path=tmp_path)
        assert success is True
        config = json.loads((tmp_path / "test-routine" / "config.json").read_text())
        assert config["scheduler"]["enabled"] is False

    def test_delete_routine_hard(self, routine_dir, tmp_path):
        success = routine_service.delete_routine("test-routine", mode="delete", base_path=tmp_path)
        assert success is True
        assert not (tmp_path / "test-routine").exists()

    def test_enable_disable_routine(self, routine_dir, tmp_path):
        routine_service.set_routine_enabled("test-routine", False, tmp_path)
        config = json.loads((tmp_path / "test-routine" / "config.json").read_text())
        assert config["scheduler"]["enabled"] is False

        routine_service.set_routine_enabled("test-routine", True, tmp_path)
        config = json.loads((tmp_path / "test-routine" / "config.json").read_text())
        assert config["scheduler"]["enabled"] is True

    def test_rename_routine(self, routine_dir, tmp_path):
        result = routine_service.rename_routine("test-routine", "renamed", tmp_path)
        assert result is not None
        assert result.name == "renamed"
        assert not (tmp_path / "test-routine").exists()

    def test_clone_routine(self, routine_dir, tmp_path):
        result = routine_service.clone_routine("test-routine", "cloned", tmp_path)
        assert result is not None
        assert result.name == "cloned"
        assert (tmp_path / "cloned" / "config.json").exists()


class TestTaskTools:
    def test_add_task(self, routine_dir, tmp_path):
        result = task_service.add_task("test-routine", {
            "task_id": "task-1",
            "schedule": {"type": "cron", "expression": "0 10 * * *"},
        }, base_path=tmp_path)
        assert result is not None
        config = json.loads((tmp_path / "test-routine" / "config.json").read_text())
        assert len(config["scheduler"]["tasks"]) == 2

    def test_add_task_duplicate_id(self, routine_dir, tmp_path):
        result = task_service.add_task("test-routine", {
            "task_id": "task-0",
            "schedule": {"type": "cron", "expression": "0 10 * * *"},
        }, base_path=tmp_path)
        assert result is None

    def test_update_task(self, routine_dir, tmp_path):
        result = task_service.update_task("test-routine", "task-0", {
            "schedule": {"type": "cron", "expression": "0 12 * * *"},
        }, base_path=tmp_path)
        assert result is not None
        assert result["schedule"]["expression"] == "0 12 * * *"

    def test_delete_task(self, routine_dir, tmp_path):
        success = task_service.delete_task("test-routine", "task-0", base_path=tmp_path)
        assert success is True
        config = json.loads((tmp_path / "test-routine" / "config.json").read_text())
        assert len(config["scheduler"]["tasks"]) == 0

    def test_enable_disable_task(self, routine_dir, tmp_path):
        success = task_service.set_task_enabled("test-routine", "task-0", False, base_path=tmp_path)
        assert success is True
        config = json.loads((tmp_path / "test-routine" / "config.json").read_text())
        assert config["scheduler"]["tasks"][0]["enabled"] is False
