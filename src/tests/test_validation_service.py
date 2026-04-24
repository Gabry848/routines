"""Tests for validation service: config validation, cron preview, task ID suggestion."""


from mcp_server.services import validation_service


class TestConfigValidation:
    def test_valid_config(self):
        config = {
            "scheduler": {
                "enabled": True,
                "timezone": "UTC",
                "tasks": [
                    {"schedule": {"type": "cron", "expression": "0 9 * * *"}},
                ],
            },
        }
        result = validation_service.validate_config(config)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_scheduler(self):
        result = validation_service.validate_config({})
        assert result.valid is False
        assert any("scheduler" in e for e in result.errors)

    def test_invalid_timezone(self):
        config = {
            "scheduler": {
                "enabled": True,
                "timezone": "Invalid/Zone",
                "tasks": [
                    {"schedule": {"type": "cron", "expression": "0 9 * * *"}},
                ],
            },
        }
        result = validation_service.validate_config(config)
        assert result.valid is False
        assert any("timezone" in e for e in result.errors)

    def test_invalid_cron(self):
        config = {
            "scheduler": {
                "enabled": True,
                "timezone": "UTC",
                "tasks": [
                    {"schedule": {"type": "cron", "expression": "not-a-cron"}},
                ],
            },
        }
        result = validation_service.validate_config(config)
        assert result.valid is False
        assert any("expression" in e for e in result.errors)

    def test_invalid_model(self):
        config = {
            "scheduler": {
                "enabled": True,
                "timezone": "UTC",
                "tasks": [
                    {"schedule": {"type": "cron", "expression": "0 9 * * *"}},
                ],
            },
            "model_config": {"model": "gpt-4"},
        }
        result = validation_service.validate_config(config)
        assert result.valid is False
        assert any("model" in e for e in result.errors)


class TestSchedulePreview:
    def test_preview_default(self):
        result = validation_service.preview_schedule("0 9 * * *")
        assert len(result) == 5
        assert all(isinstance(r, str) for r in result)

    def test_preview_custom_count(self):
        result = validation_service.preview_schedule("0 9 * * *", count=3)
        assert len(result) == 3

    def test_preview_with_timezone(self):
        result = validation_service.preview_schedule("0 9 * * *", timezone="Europe/Rome", count=2)
        assert len(result) == 2


class TestSuggestTaskId:
    def test_suggest_in_empty_routine(self, tmp_path):
        rdir = tmp_path / "routine"
        rdir.mkdir()
        (rdir / "config.json").write_text('{"scheduler": {"tasks": []}}')
        result = validation_service.suggest_task_id("routine", tmp_path)
        assert result == "task-0"

    def test_suggest_avoids_collision(self, tmp_path):
        rdir = tmp_path / "routine"
        rdir.mkdir()
        import json
        config = {"scheduler": {"tasks": [{"task_id": "task-0"}]}}
        (rdir / "config.json").write_text(json.dumps(config))
        result = validation_service.suggest_task_id("routine", tmp_path)
        assert result == "task-1"
