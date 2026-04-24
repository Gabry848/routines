import asyncio
import json

from starlette.requests import Request

from mcp_server.server import run_routine_via_api
from scheduler.engine import RoutineScheduler
from scheduler.loader import load_jobs


def _write_routine(base_path, name: str = "daily-review", task_id: str = "task-0") -> None:
    routine_dir = base_path / name
    routine_dir.mkdir()
    (routine_dir / "PROMPT.md").write_text("test prompt", encoding="utf-8")
    (routine_dir / "config.json").write_text(
        json.dumps(
            {
                "scheduler": {
                    "enabled": True,
                    "timezone": "UTC",
                    "tasks": [
                        {
                            "task_id": task_id,
                            "job_name": name,
                            "enabled": True,
                            "schedule": {"type": "cron", "expression": "0 9 * * *"},
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )


def _build_request(
    scheduler: RoutineScheduler,
    routine_name: str,
    body: bytes,
    headers: dict[str, str] | None = None,
) -> Request:
    header_items = []
    for key, value in (headers or {}).items():
        header_items.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"/api/routines/{routine_name}/run",
        "raw_path": f"/api/routines/{routine_name}/run".encode("utf-8"),
        "query_string": b"",
        "headers": header_items,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 8080),
        "state": {"scheduler": scheduler},
        "path_params": {"name": routine_name},
    }

    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


class TestApiTrigger:
    def test_post_run_endpoint_triggers_without_auth_when_env_missing(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SCHEDULER_MCP_API_KEY", raising=False)
        _write_routine(tmp_path)

        async def _run():
            scheduler = RoutineScheduler(load_jobs(tmp_path), base_path=tmp_path)
            scheduler._scheduler.start(paused=True)
            try:
                request = _build_request(scheduler, "daily-review", b"{}")
                return await run_routine_via_api(request)
            finally:
                scheduler._scheduler.shutdown(wait=False)

        response = asyncio.run(_run())

        assert response.status_code == 200
        payload = json.loads(response.body)
        assert payload["status"] == "triggered"
        assert payload["routine"] == "daily-review"
        assert payload["task_id"] is None
        assert len(payload["queued_job_ids"]) == 1

    def test_post_run_endpoint_requires_auth_when_api_key_is_configured(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SCHEDULER_MCP_API_KEY", "top-secret")
        _write_routine(tmp_path)

        async def _run():
            scheduler = RoutineScheduler(load_jobs(tmp_path), base_path=tmp_path)
            scheduler._scheduler.start(paused=True)
            try:
                unauthorized_request = _build_request(scheduler, "daily-review", b"{}")
                authorized_request = _build_request(
                    scheduler,
                    "daily-review",
                    b'{"task_id":"task-0"}',
                    headers={"Authorization": "Bearer top-secret"},
                )
                unauthorized = await run_routine_via_api(unauthorized_request)
                authorized = await run_routine_via_api(authorized_request)
                return unauthorized, authorized
            finally:
                scheduler._scheduler.shutdown(wait=False)

        unauthorized, authorized = asyncio.run(_run())

        assert unauthorized.status_code == 401
        assert authorized.status_code == 200
        payload = json.loads(authorized.body)
        assert payload["task_id"] == "task-0"
        assert len(payload["queued_job_ids"]) == 1

    def test_post_run_endpoint_returns_404_for_unknown_routine(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SCHEDULER_MCP_API_KEY", raising=False)

        async def _run():
            scheduler = RoutineScheduler(load_jobs(tmp_path), base_path=tmp_path)
            scheduler._scheduler.start(paused=True)
            try:
                request = _build_request(scheduler, "missing", b"{}")
                return await run_routine_via_api(request)
            finally:
                scheduler._scheduler.shutdown(wait=False)

        response = asyncio.run(_run())

        assert response.status_code == 404
        payload = json.loads(response.body)
        assert "no matching jobs" in payload["error"]

    def test_post_run_endpoint_rejects_invalid_json(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SCHEDULER_MCP_API_KEY", raising=False)
        _write_routine(tmp_path)

        async def _run():
            scheduler = RoutineScheduler(load_jobs(tmp_path), base_path=tmp_path)
            scheduler._scheduler.start(paused=True)
            try:
                request = _build_request(
                    scheduler,
                    "daily-review",
                    b"{invalid",
                    headers={"Content-Type": "application/json"},
                )
                return await run_routine_via_api(request)
            finally:
                scheduler._scheduler.shutdown(wait=False)

        response = asyncio.run(_run())

        assert response.status_code == 400
        payload = json.loads(response.body)
        assert payload["error"] == "invalid json body"
