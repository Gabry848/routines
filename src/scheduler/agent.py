from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    query,
)


class ClaudeAgent:
    def __init__(self, options: ClaudeAgentOptions) -> None:
        self.options = options

    async def run(self, prompt: str) -> None:
        log = ""
        async for message in query(prompt=prompt, options=self.options):
            match message:
                case AssistantMessage():
                    for block in message.content:
                        if hasattr(block, "text"):
                            log += block.text + "\n"
                        elif hasattr(block, "name"):
                            log += f"[tool: {block.name}] {block.input}" + "\n"
                case ResultMessage():
                    log += (
                        f"\nDone - cost: ${message.total_cost_usd:.4f}, turns: {message.num_turns}"
                        + "\n"
                    )
                case SystemMessage():
                    pass
        self.write_log(log)

    def write_log(self, text: str) -> None:
        cwd_path = Path(self.options.cwd)
        log_dir = cwd_path / "logs"

        routine_log_dir = cwd_path.parent / "logs"
        if cwd_path.name == "env" and routine_log_dir.exists():
            log_dir = routine_log_dir

        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{datetime.now().isoformat()}.log"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{datetime.now().isoformat()} - {text}\n")
