from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskSummary(BaseModel):
    task_id: str
    job_name: str | None = None
    cron: str
    timezone: str
    enabled: bool = True
    next_run: str | None = None


class RoutineSummary(BaseModel):
    name: str
    enabled: bool
    path: str
    tasks: list[TaskSummary] = Field(default_factory=list)


class RoutineDetail(BaseModel):
    name: str
    enabled: bool
    path: str
    config: dict[str, Any]
    prompt_text: str
    tasks: list[TaskSummary] = Field(default_factory=list)


class SchedulerStatus(BaseModel):
    status: str
    started_at: str | None = None
    last_sync_at: str | None = None
    polling_interval_seconds: int
    active_job_count: int
    total_routines: int
    enabled_routines: int


class ExecutionInfo(BaseModel):
    execution_id: str
    routine_name: str
    task_id: str
    started_at: str
    finished_at: str | None = None
    status: str
    duration_seconds: float | None = None


class ErrorInfo(BaseModel):
    routine_name: str
    task_id: str
    error_type: str
    message: str
    timestamp: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class DriftResult(BaseModel):
    in_memory_only: list[str] = Field(default_factory=list)
    on_disk_only: list[str] = Field(default_factory=list)
    config_changed: list[str] = Field(default_factory=list)


class ScriptTestResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class PromptTestResult(BaseModel):
    prompt_file: str | None = None
    length: int = 0
    word_count: int = 0
    issues: list[str] = Field(default_factory=list)


class ExportPayload(BaseModel):
    name: str
    config: dict[str, Any]
    prompt_text: str
    files: list[str] = Field(default_factory=list)
