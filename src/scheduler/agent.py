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

    def _log_path(self) -> Path:
        cwd_path = Path(self.options.cwd)
        routine_log_dir = cwd_path.parent / "logs"
        if cwd_path.name == "env" and routine_log_dir.exists():
            log_dir = routine_log_dir
        else:
            log_dir = cwd_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{datetime.now().isoformat()}.log"

    async def run(self, prompt: str) -> None:
        log_path = self._log_path()
        with log_path.open("a", encoding="utf-8") as log_file:
            async for message in query(prompt=prompt, options=self.options):
                match message:
                    case AssistantMessage():
                        for block in message.content:
                            if hasattr(block, "text"):
                                log_file.write(block.text + "\n")
                            elif hasattr(block, "name"):
                                log_file.write(f"[tool: {block.name}] {block.input}\n")
                            log_file.flush()
                    case ResultMessage():
                        log_file.write(
                            f"\nDone - cost: ${message.total_cost_usd:.4f}, turns: {message.num_turns}\n"
                        )
                        log_file.flush()
                    case SystemMessage():
                        pass

