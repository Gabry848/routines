from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTINES_PATH = PROJECT_ROOT / "routines"
DEFAULT_TOOLS = ["Bash", "Read", "Edit"]
DEFAULT_MODEL = "sonnet"
PROMT_FILENAME_CANDIDATES = ["prompt.md", "promt.md", "PROMPT.md", "PROMT.md"]