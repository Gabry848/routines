from __future__ import annotations

from pathlib import Path

from ..server import mcp


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ROUTINE_CONFIG_SKILL_PATH = PROJECT_ROOT / "skills" / "routine-config-reference.md"


@mcp.resource(
    "scheduler://guides/routine-config",
    name="routine-config-guide",
    title="Routine Config Guide",
    description="Detailed reference for building a valid routine config.json payload before calling add_routine.",
    mime_type="text/markdown",
)
def routine_config_guide() -> str:
    return ROUTINE_CONFIG_SKILL_PATH.read_text(encoding="utf-8")
