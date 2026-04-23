from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTINES_PATH = PROJECT_ROOT / "routines"
LOCAL_CONFIG_PATH = PROJECT_ROOT / ".config" / "routines"
LOCAL_CLAUDE_DIR = LOCAL_CONFIG_PATH / "claude"
LOCAL_CLAUDE_SETTINGS_PATH = LOCAL_CLAUDE_DIR / "settings.json"
LOCAL_CLAUDE_JSON_PATH = LOCAL_CONFIG_PATH / "claude.json"
DEFAULT_TOOLS = ["Bash", "Read", "Edit"]
DEFAULT_MODEL = "sonnet"
PROMT_FILENAME_CANDIDATES = ["prompt.md", "promt.md", "PROMPT.md", "PROMT.md"]
