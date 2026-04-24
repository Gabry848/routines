"""Tests for MCP tool functions with mock scheduler."""

import json
import pytest

from mcp_server.services import routine_service, task_service
from mcp_server.tools.import_export_tools import import_routine
from mcp_server.tools.routine_tools import add_routine, update_routine_config
from mcp_server.tools.task_tools import add_task_to_routine, update_task as update_task_tool


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
        config = {
            "scheduler": {
                "enabled": True,
                "timezone": "UTC",
                "tasks": [
                    {"task_id": "task-0", "schedule": {"type": "cron", "expression": "0 9 * * *"}},
                ],
            },
            "model_config": {},
        }
        result = routine_service.create_routine("new-routine", config, "hello", tmp_path)
        assert result is not None
        assert result.name == "new-routine"
        assert (tmp_path / "new-routine" / "config.json").exists()
        assert (tmp_path / "new-routine" / "PROMPT.md").exists()

    def test_create_routine_duplicate(self, routine_dir, tmp_path):
        config = {
            "scheduler": {
                "enabled": True,
                "timezone": "UTC",
                "tasks": [
                    {"task_id": "task-0", "schedule": {"type": "cron", "expression": "0 9 * * *"}},
                ],
            },
            "model_config": {},
        }
        result = routine_service.create_routine("test-routine", config, "hello", tmp_path)
        assert result is None

    def test_add_routine_normalizes_and_filters_config(self, monkeypatch, tmp_path):
        captured: dict[str, object] = {}

        def fake_create_routine(name, config, prompt):
            captured["name"] = name
            captured["config"] = config
            captured["prompt"] = prompt

            class _Result:
                def model_dump(self):
                    return {"name": name, "config": config, "prompt_text": prompt}

            return _Result()

        monkeypatch.setattr(routine_service, "create_routine", fake_create_routine)

        result = add_routine(
            None,
            "daily-review",
            {
                "scheduler": {
                    "tasks": [{"schedule": {"expression": "0 9 * * *"}, "ignored": True}],
                },
                "model_config": {"env": {"FOO": "bar"}, "ignored": True},
                "ignored": True,
            },
            "hello",
        )

        assert captured["name"] == "daily-review"
        normalized = captured["config"]
        assert isinstance(normalized, dict)
        assert normalized["scheduler"]["enabled"] is True
        assert normalized["scheduler"]["timezone"] == "Europe/Rome"
        assert normalized["scheduler"]["tasks"][0]["job_name"] == "daily-review"
        assert normalized["scheduler"]["tasks"][0]["task_id"] == "task-0"
        assert "ignored" not in normalized
        assert "ignored" not in normalized["model_config"]
        assert result["name"] == "daily-review"

    def test_add_routine_rejects_invalid_config(self, monkeypatch):
        called = False

        def fake_create_routine(name, config, prompt):
            nonlocal called
            called = True
            return None

        monkeypatch.setattr(routine_service, "create_routine", fake_create_routine)

        result = add_routine(
            None,
            "daily-review",
            {"scheduler": {"enabled": True, "tasks": [{"schedule": {"expression": "bad-cron"}}]}},
            "hello",
        )

        assert result["error"] == "invalid routine config"
        assert any("expression invalid" in entry for entry in result["validation_errors"])
        assert called is False

    def test_update_routine_config_replaces_with_normalized_config(self, monkeypatch):
        current = type(
            "RoutineDetailStub",
            (),
            {
                "config": {
                    "scheduler": {
                        "enabled": True,
                        "timezone": "UTC",
                        "tasks": [
                            {
                                "task_id": "task-0",
                                "job_name": "daily-review",
                                "enabled": True,
                                "schedule": {"type": "cron", "expression": "0 9 * * *"},
                                "legacy": True,
                            }
                        ],
                        "legacy": True,
                    },
                    "model_config": {"model": "sonnet", "legacy": True},
                    "legacy": True,
                }
            },
        )()
        captured: dict[str, object] = {}

        def fake_get_routine(name, task_id=None):
            return current

        def fake_replace_routine_config(name, config):
            captured["name"] = name
            captured["config"] = config
            return config

        monkeypatch.setattr(routine_service, "get_routine", fake_get_routine)
        monkeypatch.setattr(routine_service, "replace_routine_config", fake_replace_routine_config)

        result = update_routine_config(
            None,
            "daily-review",
            {"model_config": {"env": {"FOO": "bar"}}, "ignored": True},
        )

        normalized = captured["config"]
        assert isinstance(normalized, dict)
        assert normalized["scheduler"]["tasks"][0]["job_name"] == "daily-review"
        assert "legacy" not in normalized
        assert "legacy" not in normalized["scheduler"]
        assert "legacy" not in normalized["scheduler"]["tasks"][0]
        assert "legacy" not in normalized["model_config"]
        assert result["model_config"]["env"] == {"FOO": "bar"}

    def test_update_routine_config_rejects_invalid_merged_result(self, monkeypatch):
        current = type(
            "RoutineDetailStub",
            (),
            {
                "config": {
                    "scheduler": {
                        "enabled": True,
                        "timezone": "UTC",
                        "tasks": [
                            {
                                "task_id": "task-0",
                                "job_name": "daily-review",
                                "enabled": True,
                                "schedule": {"type": "cron", "expression": "0 9 * * *"},
                            }
                        ],
                    }
                }
            },
        )()

        monkeypatch.setattr(routine_service, "get_routine", lambda name, task_id=None: current)

        result = update_routine_config(
            None,
            "daily-review",
            {"scheduler": {"tasks": [{"schedule": {"expression": "bad-cron"}}]}},
        )

        assert result["error"] == "invalid routine config update"
        assert any("expression invalid" in entry for entry in result["validation_errors"])

    def test_import_routine_normalizes_and_validates(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_import_routine(name, config, prompt):
            captured["name"] = name
            captured["config"] = config

            class _Result:
                def model_dump(self):
                    return {"name": name, "config": config, "prompt_text": prompt}

            return _Result()

        monkeypatch.setattr(routine_service, "import_routine", fake_import_routine)

        result = import_routine(
            None,
            "nightly-job",
            {"scheduler": {"tasks": [{"schedule": {"expression": "0 1 * * *"}}]}},
            "prompt",
        )

        normalized = captured["config"]
        assert normalized["scheduler"]["tasks"][0]["task_id"] == "task-0"
        assert normalized["scheduler"]["tasks"][0]["job_name"] == "nightly-job"
        assert result["name"] == "nightly-job"

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

    def test_add_task_tool_normalizes_and_validates(self, monkeypatch):
        current = type(
            "RoutineDetailStub",
            (),
            {
                "config": {
                    "scheduler": {
                        "tasks": [
                            {"task_id": "task-0", "schedule": {"type": "cron", "expression": "0 9 * * *"}}
                        ]
                    }
                }
            },
        )()
        captured: dict[str, object] = {}

        def fake_add_task(name, task):
            captured["task"] = task
            return task

        monkeypatch.setattr(routine_service, "get_routine", lambda name: current)
        monkeypatch.setattr(task_service, "add_task", fake_add_task)

        result = add_task_to_routine(
            None,
            "test-routine",
            {"schedule": {"expression": "0 10 * * *"}, "ignored": True},
        )

        normalized = captured["task"]
        assert isinstance(normalized, dict)
        assert normalized["task_id"] == "task-1"
        assert normalized["job_name"] == "test-routine"
        assert "ignored" not in normalized
        assert result["task_id"] == "task-1"

    def test_add_task_tool_rejects_invalid_task(self, monkeypatch):
        current = type(
            "RoutineDetailStub",
            (),
            {"config": {"scheduler": {"tasks": []}}},
        )()

        monkeypatch.setattr(routine_service, "get_routine", lambda name: current)

        result = add_task_to_routine(
            None,
            "test-routine",
            {"schedule": {"expression": "bad-cron"}},
        )

        assert result["error"] == "invalid task payload"
        assert any("expression invalid" in entry for entry in result["validation_errors"])

    def test_update_task_tool_replaces_and_filters_fields(self, monkeypatch):
        current = type(
            "RoutineDetailStub",
            (),
            {
                "config": {
                    "scheduler": {
                        "tasks": [
                            {
                                "task_id": "task-0",
                                "job_name": "test-routine",
                                "enabled": True,
                                "schedule": {"type": "cron", "expression": "0 9 * * *"},
                                "legacy": True,
                            }
                        ]
                    }
                }
            },
        )()
        captured: dict[str, object] = {}

        def fake_replace_task(name, task_id, new_task):
            captured["task"] = new_task
            return new_task

        monkeypatch.setattr(routine_service, "get_routine", lambda name: current)
        monkeypatch.setattr(task_service, "replace_task", fake_replace_task)

        result = update_task_tool(
            None,
            "test-routine",
            "task-0",
            {"schedule": {"expression": "0 12 * * *"}, "ignored": True},
        )

        normalized = captured["task"]
        assert isinstance(normalized, dict)
        assert normalized["schedule"]["expression"] == "0 12 * * *"
        assert "legacy" not in normalized
        assert "ignored" not in normalized
        assert result["task_id"] == "task-0"

    def test_update_task_tool_rejects_duplicate_task_id(self, monkeypatch):
        current = type(
            "RoutineDetailStub",
            (),
            {
                "config": {
                    "scheduler": {
                        "tasks": [
                            {
                                "task_id": "task-0",
                                "job_name": "test-routine",
                                "enabled": True,
                                "schedule": {"type": "cron", "expression": "0 9 * * *"},
                            },
                            {
                                "task_id": "task-1",
                                "job_name": "test-routine",
                                "enabled": True,
                                "schedule": {"type": "cron", "expression": "0 10 * * *"},
                            },
                        ]
                    }
                }
            },
        )()

        monkeypatch.setattr(routine_service, "get_routine", lambda name: current)

        result = update_task_tool(
            None,
            "test-routine",
            "task-0",
            {"task_id": "task-1"},
        )

        assert result["error"] == "invalid task update"
        assert any("already exists" in entry for entry in result["validation_errors"])

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
