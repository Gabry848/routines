from pathlib import Path

ROUTINES_PATH = Path(__file__).resolve().parent.parent.parent / "routines"
DEFAULT_TOOLS = ["Bash", "Read", "Edit"]
DEFAULT_MODEL = "sonnet"
PROMT_FILENAME_CANDIDATES = ["prompt.md", "promt.md", "PROMPT.md", "PROMT.md"]