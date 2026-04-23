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
        # Se siamo in una run isolata (envs/2026-XX-YY), risaliamo fino alla vera root della routine
        if cwd_path.parent.name == "envs":
            routine_root = cwd_path.parent.parent
        else:
            routine_root = cwd_path.parent
            
        log_dir = routine_root / "logs"
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

