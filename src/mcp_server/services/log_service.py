from __future__ import annotations

from pathlib import Path
from typing import Any

from scheduler.constants import ROUTINES_PATH


def get_logs(
    routine_name: str,
    limit: int = 5,
    base_path: Path = ROUTINES_PATH,
) -> list[dict[str, Any]]:
    logs_dir = base_path / routine_name / "logs"
    if not logs_dir.exists():
        return []

    log_files = sorted(logs_dir.glob("*.log"), reverse=True)[:limit]
    results = []
    for log_path in log_files:
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = f"<error reading {log_path.name}>"
        results.append({
            "filename": log_path.name,
            "path": str(log_path),
            "size_bytes": log_path.stat().st_size,
            "content": content,
        })
    return results


def get_log_by_execution_id(
    execution_id: str,
    base_path: Path = ROUTINES_PATH,
) -> dict[str, Any] | None:
    # Execution IDs contain a timestamp suffix like 20260423145515123456
    # Log filenames are like 2026-04-23T14:55:15.123456.log
    # Extract timestamp part from execution_id
    parts = execution_id.split(":")
    if len(parts) < 3:
        return None

    timestamp_str = parts[-1]  # e.g., 20260423145515123456
    if len(timestamp_str) < 14:
        return None

    # Parse to find matching log
    try:
        year = timestamp_str[0:4]
        month = timestamp_str[4:6]
        day = timestamp_str[6:8]
        hour = timestamp_str[8:10]
        minute = timestamp_str[10:12]
        second = timestamp_str[12:14]
    except (ValueError, IndexError):
        return None

    routine_name = parts[0]
    logs_dir = base_path / routine_name / "logs"
    if not logs_dir.exists():
        return None

    # Find log file matching the approximate timestamp
    for log_path in sorted(logs_dir.glob("*.log"), reverse=True):
        name = log_path.name
        if (year in name and month in name and day in name
                and hour in name and minute in name and second in name):
            content = log_path.read_text(encoding="utf-8", errors="replace")
            return {
                "filename": name,
                "path": str(log_path),
                "execution_id": execution_id,
                "content": content,
            }

    return None
