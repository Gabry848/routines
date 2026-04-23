#!/usr/bin/env python3
"""Textual TUI wizard for creating new routines."""

import json
import re
import stat
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.validation import ValidationResult, Validator
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    SelectionList,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
)
from textual.widgets._selection_list import Selection

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTINES_PATH = PROJECT_ROOT / "routines"

COMMON_TIMEZONES = [
    "UTC",
    "Europe/Rome",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Sao_Paulo",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Australia/Sydney",
]

BUILTIN_TOOLS = [
    "Bash",
    "Read",
    "Edit",
    "Write",
    "GlobMatch",
    "GrepSearch",
    "LS",
    "View",
    "FileRead",
    "FileWrite",
]

CRON_PRESETS = [
    ("Every day at 09:00", "0 9 * * *"),
    ("Weekdays at 09:00", "0 9 * * 1-5"),
    ("Every hour", "0 * * * *"),
    ("Every 30 minutes", "*/30 * * * *"),
    ("Twice daily (09:00, 18:00)", "0 9,18 * * *"),
    ("Every Monday at 08:00", "0 8 * * 1"),
]

MODELS = [
    ("sonnet", "Sonnet — good balance, default"),
    ("opus", "Opus — most capable, expensive"),
    ("haiku", "Haiku — fastest, cheapest"),
]

STEP_TITLES = [
    "Routine Name",
    "Schedule",
    "Timezone",
    "Model",
    "MCP Servers",
    "MCP Tools",
    "Built-in Tools",
    "Docker",
    "Environment",
    "Prompt",
    "Setup Script",
    "Summary",
]

class KebabCaseValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("Name is required")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            return self.failure("Must be kebab-case: lowercase letters, numbers, hyphens only")
        if (ROUTINES_PATH / value).exists():
            return self.failure(f"Routine '{value}' already exists")
        return self.success()


class CreateRoutineApp(App):
    CSS = """
    .screen {
        height: 1fr;
    }

    .main {
        height: 1fr;
        padding: 1 2;
    }

    .step-title {
        width: 1fr;
        text-align: center;
        text-style: bold;
        margin-bottom: 0;
        color: $text;
    }

    #step-subtitle {
        width: 1fr;
        text-align: center;
        margin-bottom: 1;
        color: $text-disabled;
    }

    .info {
        color: $text-disabled;
        margin-bottom: 1;
    }

    .section-label {
        text-style: bold;
        margin-bottom: 0;
    }

    SelectionList {
        height: auto;
        max-height: 16;
    }

    .presets-row {
        height: auto;
        margin-bottom: 1;
    }

    .preset-btn {
        margin: 0 1 0 0;
    }

    .summary-block {
        margin-bottom: 1;
        padding: 1;
        border: round $primary;
    }

    TabbedContent {
        height: auto;
        max-height: 14;
    }

    TextArea {
        height: 12;
    }

    .small-textarea {
        height: 8;
    }

    .mcp-none {
        color: $text-disabled;
        padding: 1;
    }

    .nav-bar {
        height: 3;
        padding: 0 2;
        align: left middle;
    }

    #footer-progress {
        width: 1fr;
        color: $success;
    }

    #footer-actions {
        width: auto;
    }

    .docker-fields {
        margin-top: 1;
    }

    .env-fields {
        margin-top: 1;
    }

    #btn-next {
        margin-left: 1;
    }

    #btn-back {
        margin-right: 1;
    }
    """

    TITLE = "Create Routine"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="screen"):
            with VerticalScroll(classes="main"):
                yield Label(id="step-title", classes="step-title")
                yield Static(id="step-subtitle")
                yield VerticalScroll(id="content")
            with Horizontal(classes="nav-bar"):
                yield Static(id="footer-progress")
                with Horizontal(id="footer-actions"):
                    yield Button("< Back", id="btn-back", disabled=True)
                    yield Button("Next >", id="btn-next", variant="primary")
        yield Footer()

        self._current_step = 0
        self._data: dict = {}

    async def on_mount(self) -> None:
        await self._render_step(0)
        self.query_one("#btn-next").focus()

    async def _render_step(self, step: int) -> None:
        self._current_step = step

        visible_steps = self._visible_steps(step)
        visible_index = visible_steps.index(step)
        visible_total = len(visible_steps)

        self.query_one("#step-title", Label).update(
            f"Passaggio {visible_index + 1:02d} di {visible_total:02d}"
        )
        self.query_one("#step-subtitle", Static).update(STEP_TITLES[step])
        self.query_one("#footer-progress", Static).update(
            self._render_progress_bar(visible_index + 1, visible_total)
        )

        content = self.query_one("#content", VerticalScroll)
        await content.remove_children()

        builder = getattr(self, f"_build_step_{step}", None)
        if builder:
            builder(content)

        self.query_one("#btn-back", Button).disabled = step == 0
        next_btn = self.query_one("#btn-next", Button)
        if step == len(STEP_TITLES) - 1:
            next_btn.label = "Create"
            next_btn.variant = "success"
        else:
            next_btn.label = "Next >"
            next_btn.variant = "primary"

    def _visible_steps(self, current_step: int) -> list[int]:
        return [
            index
            for index in range(len(STEP_TITLES))
            if index != 5 or current_step <= 5 or self._data.get("mcp_servers")
        ]

    def _render_progress_bar(self, current: int, total: int, width: int = 24) -> str:
        filled = max(1, round((current / total) * width))
        return f"[{'█' * filled}{'░' * (width - filled)}] {current}/{total}"

    def _collect_step(self, step: int) -> bool:
        collector = getattr(self, f"_collect_step_{step}", None)
        if collector:
            return collector()
        return True

    def _should_skip(self, step: int) -> bool:
        return step == 5 and not self._data.get("mcp_servers")

    @on(Button.Pressed, "#btn-next")
    async def on_next(self) -> None:
        if not self._collect_step(self._current_step):
            return
        target = self._current_step + 1
        while target < len(STEP_TITLES) and self._should_skip(target):
            target += 1
        if target >= len(STEP_TITLES):
            target = len(STEP_TITLES) - 1
        await self._render_step(target)

    @on(Button.Pressed, "#btn-back")
    async def on_back(self) -> None:
        target = self._current_step - 1
        while target > 0 and self._should_skip(target):
            target -= 1
        await self._render_step(target)

    # ── Step 0: Routine Name ─────────────────────────────

    def _build_step_0(self, container: VerticalScroll) -> None:
        container.mount(
            Label("Enter a unique name for your routine (kebab-case).", classes="info"),
            Input(
                placeholder="e.g. my-routine-name",
                validators=[KebabCaseValidator()],
                id="routine-name-input",
            ),
        )
        inp = container.query_one("#routine-name-input", Input)
        if self._data.get("routine_name"):
            inp.value = self._data["routine_name"]
        inp.focus()

    def _collect_step_0(self) -> bool:
        inp = self.query_one("#routine-name-input", Input)
        if not inp.value.strip():
            return False
        self._data["routine_name"] = inp.value.strip()
        return True

    # ── Step 1: Schedule ─────────────────────────────────

    def _build_step_1(self, container: VerticalScroll) -> None:
        preset_buttons = []
        for label, expr in CRON_PRESETS:
            btn = Button(label, classes="preset-btn")
            btn._cron_expr = expr
            preset_buttons.append(btn)
        preset_row = Horizontal(*preset_buttons, classes="presets-row", id="presets-row")
        container.mount(
            Label("Choose a cron expression or pick a preset.", classes="info"),
            preset_row,
            Input(
                placeholder="0 9 * * *",
                value=self._data.get("cron_expression", "0 9 * * *"),
                id="cron-input",
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        expr = getattr(event.button, "_cron_expr", None)
        if expr and self._current_step == 1:
            try:
                inp = self.query_one("#cron-input", Input)
                inp.value = expr
            except Exception:
                pass

    def _collect_step_1(self) -> bool:
        inp = self.query_one("#cron-input", Input)
        val = inp.value.strip()
        if not val:
            return False
        try:
            import croniter
            croniter.croniter(val)
        except Exception:
            return False
        self._data["cron_expression"] = val
        return True

    # ── Step 2: Timezone ─────────────────────────────────

    def _build_step_2(self, container: VerticalScroll) -> None:
        container.mount(
            Label("Enter IANA timezone. Common options:", classes="info"),
            Static("  ".join(COMMON_TIMEZONES), classes="info"),
            Input(
                placeholder="Europe/Rome",
                value=self._data.get("timezone", "Europe/Rome"),
                id="tz-input",
            ),
        )

    def _collect_step_2(self) -> bool:
        inp = self.query_one("#tz-input", Input)
        self._data["timezone"] = inp.value.strip() or "UTC"
        return True

    # ── Step 3: Model ────────────────────────────────────

    def _build_step_3(self, container: VerticalScroll) -> None:
        container.mount(Label("Select the Claude model.", classes="info"))
        current = self._data.get("model", "sonnet")
        radio_buttons = []
        for model_id, desc in MODELS:
            radio_buttons.append(
                RadioButton(
                    f"{model_id} — {desc}",
                    value=model_id == current,
                    name=model_id,
                )
            )
        radio = RadioSet(*radio_buttons, id="model-radio")
        container.mount(radio)

    def _collect_step_3(self) -> bool:
        radio = self.query_one("#model-radio", RadioSet)
        if radio.pressed_button:
            self._data["model"] = radio.pressed_button.name or "sonnet"
        else:
            self._data["model"] = "sonnet"
        return True

    # ── Step 4: MCP Servers ──────────────────────────────

    def _build_step_4(self, container: VerticalScroll) -> None:
        from scheduler.mcp_config import discover_mcp_servers
        servers = discover_mcp_servers(PROJECT_ROOT)

        if not servers:
            container.mount(
                Static(
                    "No MCP servers found.\n"
                    "Configure servers in ~/.claude.json or .mcp.json first.",
                    classes="mcp-none",
                )
            )
            return

        container.mount(Label("Select MCP servers to enable.", classes="info"))
        options = []
        for name, cfg in sorted(servers.items()):
            server_type = cfg.get("type", "stdio")
            desc = ""
            if "url" in cfg:
                desc = cfg["url"][:60]
            elif "command" in cfg:
                desc = f"{cfg['command']} {' '.join(cfg.get('args', [])[:2])}"
            label = f"{name}  [{server_type}]"
            if desc:
                label += f"  — {desc}"
            options.append(Selection(label, name))

        sl = SelectionList[str](*options, id="mcp-server-list")
        container.mount(sl)

        selected = self._data.get("mcp_servers", [])
        if selected:
            for name in selected:
                sl.select(name)

    def _collect_step_4(self) -> bool:
        try:
            sl = self.query_one("#mcp-server-list", SelectionList)
            selected = list(sl.selected)
        except Exception:
            selected = []
        self._data["mcp_servers"] = selected
        if not selected:
            self._data.pop("mcp_selected_tools", None)
        return True

    # ── Step 5: MCP Tools ────────────────────────────────

    def _build_step_5(self, container: VerticalScroll) -> None:
        servers = self._data.get("mcp_servers", [])
        if not servers:
            return

        container.mount(
            Label(
                "For each MCP server, enter specific tools to enable (one per line).\n"
                "Leave empty to allow ALL tools from that server.",
                classes="info",
            )
        )

        panes = []
        for server_name in servers:
            current_tools = self._data.get("mcp_selected_tools", {}).get(server_name, [])
            text = "\n".join(current_tools)
            ta = TextArea(text, language="text", id=f"tools-{server_name}", classes="small-textarea")
            pane = TabPane(server_name, ta, id=f"tab-{server_name}")
            panes.append(pane)

        tc = TabbedContent(*panes, id="mcp-tools-tabs")
        container.mount(tc)

    def _collect_step_5(self) -> bool:
        servers = self._data.get("mcp_servers", [])
        if not servers:
            return True
        selected_tools: dict[str, list[str]] = {}
        for server_name in servers:
            try:
                ta = self.query_one(f"#tools-{server_name}", TextArea)
                text = ta.text.strip()
                if text:
                    tools = [t.strip() for t in text.splitlines() if t.strip()]
                    selected_tools[server_name] = tools
            except Exception:
                pass
        self._data["mcp_selected_tools"] = selected_tools
        return True

    # ── Step 6: Built-in Tools ───────────────────────────

    def _build_step_6(self, container: VerticalScroll) -> None:
        container.mount(Label("Select built-in tools to allow.", classes="info"))
        default_tools = self._data.get("allowed_tools", ["Bash", "Read", "Edit"])
        options = []
        for tool in BUILTIN_TOOLS:
            options.append(Selection(tool, tool))
        sl = SelectionList[str](*options, id="builtin-tools-list")
        container.mount(sl)
        for tool_name in default_tools:
            sl.select(tool_name)

    def _collect_step_6(self) -> bool:
        try:
            sl = self.query_one("#builtin-tools-list", SelectionList)
            self._data["allowed_tools"] = list(sl.selected)
        except Exception:
            self._data["allowed_tools"] = ["Bash", "Read", "Edit"]
        return True

    # ── Step 7: Docker ───────────────────────────────────

    def _build_step_7(self, container: VerticalScroll) -> None:
        enabled = self._data.get("docker_enabled", False)
        container.mount(
            Label("Enable Docker sandboxing?", classes="info"),
            Switch(value=enabled, id="docker-switch"),
            Vertical(id="docker-fields"),
        )
        if enabled:
            self._show_docker_fields(container.query_one("#docker-fields", Vertical))

    @on(Switch.Changed, "#docker-switch")
    def on_docker_toggle(self, event: Switch.Changed) -> None:
        fields = self.query_one("#docker-fields", Vertical)
        fields.remove_children()
        if event.value:
            self._show_docker_fields(fields)

    def _show_docker_fields(self, container: Vertical) -> None:
        container.mount(
            Label("Image:", classes="section-label"),
            Input(value=self._data.get("docker_image", "node:20"), id="docker-image"),
            Label("Network:", classes="section-label"),
            Input(value=self._data.get("docker_network", "bridge"), id="docker-network"),
            Label("Extra volumes (one per line):", classes="section-label"),
            TextArea(
                "\n".join(self._data.get("docker_extra_volumes", [])),
                language="text",
                id="docker-volumes",
                classes="small-textarea",
            ),
        )

    def _collect_step_7(self) -> bool:
        switch = self.query_one("#docker-switch", Switch)
        self._data["docker_enabled"] = switch.value
        if switch.value:
            try:
                self._data["docker_image"] = self.query_one("#docker-image", Input).value.strip() or "node:20"
                self._data["docker_network"] = self.query_one("#docker-network", Input).value.strip() or "bridge"
                vol_text = self.query_one("#docker-volumes", TextArea).text.strip()
                self._data["docker_extra_volumes"] = (
                    [v.strip() for v in vol_text.splitlines() if v.strip()]
                    if vol_text else []
                )
            except Exception:
                self._data["docker_image"] = "node:20"
                self._data["docker_network"] = "bridge"
                self._data["docker_extra_volumes"] = []
        return True

    # ── Step 8: Environment ──────────────────────────────

    def _build_step_8(self, container: VerticalScroll) -> None:
        container.mount(Label("Configure environment options.", classes="info"))

        isolated = self._data.get("isolated_runs", False)
        keep = self._data.get("keep_executions", False)
        clone = self._data.get("clone_repo", "")

        container.mount(
            Switch(value=isolated, id="isolated-switch"),
            Label("  Isolated runs (each execution gets own directory)"),
            Switch(value=keep, id="keep-switch"),
            Label("  Keep executions (don't delete ephemeral dirs)"),
            Switch(value=bool(clone), id="clone-switch"),
            Label("  Clone git repository"),
            Vertical(id="env-fields"),
        )
        if clone:
            self._show_clone_fields(container.query_one("#env-fields", Vertical))

    @on(Switch.Changed, "#clone-switch")
    def on_clone_toggle(self, event: Switch.Changed) -> None:
        fields = self.query_one("#env-fields", Vertical)
        fields.remove_children()
        if event.value:
            self._show_clone_fields(fields)

    def _show_clone_fields(self, container: Vertical) -> None:
        container.mount(
            Input(
                placeholder="https://github.com/user/repo",
                value=self._data.get("clone_repo", ""),
                id="clone-repo-input",
            ),
            Label("Branch:", classes="section-label"),
            Input(
                placeholder="main",
                value=self._data.get("clone_branch", "main"),
                id="clone-branch-input",
            ),
        )

    def _collect_step_8(self) -> bool:
        self._data["isolated_runs"] = self.query_one("#isolated-switch", Switch).value
        self._data["keep_executions"] = self.query_one("#keep-switch", Switch).value
        clone = self.query_one("#clone-switch", Switch).value
        if clone:
            try:
                self._data["clone_repo"] = self.query_one("#clone-repo-input", Input).value.strip()
                self._data["clone_branch"] = self.query_one("#clone-branch-input", Input).value.strip() or "main"
            except Exception:
                self._data["clone_repo"] = ""
        else:
            self._data["clone_repo"] = ""
        return True

    # ── Step 9: Prompt ───────────────────────────────────

    def _build_step_9(self, container: VerticalScroll) -> None:
        container.mount(
            Label("Write the prompt for the Claude agent (PROMT.md).", classes="info"),
            TextArea(
                self._data.get("prompt_text", ""),
                language="markdown",
                id="prompt-area",
            ),
        )

    def _collect_step_9(self) -> bool:
        ta = self.query_one("#prompt-area", TextArea)
        self._data["prompt_text"] = ta.text
        return True

    # ── Step 10: Setup Script ────────────────────────────

    def _build_step_10(self, container: VerticalScroll) -> None:
        enabled = self._data.get("setup_script_enabled", False)
        container.mount(
            Label("Add a setup script that runs before each execution?", classes="info"),
            Switch(value=enabled, id="setup-switch"),
            Vertical(id="setup-fields"),
        )
        if enabled:
            self._show_setup_fields(container.query_one("#setup-fields", Vertical))

    @on(Switch.Changed, "#setup-switch")
    def on_setup_toggle(self, event: Switch.Changed) -> None:
        fields = self.query_one("#setup-fields", Vertical)
        fields.remove_children()
        if event.value:
            self._show_setup_fields(fields)

    def _show_setup_fields(self, container: Vertical) -> None:
        name = self._data.get("routine_name", "my-routine")
        default = f"""#!/usr/bin/env sh
set -eu
echo "Routine {name} avviata in $(pwd)"
"""
        container.mount(
            TextArea(
                self._data.get("setup_script", default),
                language="shell",
                id="setup-area",
            ),
        )

    def _collect_step_10(self) -> bool:
        switch = self.query_one("#setup-switch", Switch)
        self._data["setup_script_enabled"] = switch.value
        if switch.value:
            try:
                ta = self.query_one("#setup-area", TextArea)
                self._data["setup_script"] = ta.text
            except Exception:
                pass
        return True

    # ── Step 11: Summary ─────────────────────────────────

    def _build_step_11(self, container: VerticalScroll) -> None:
        d = self._data
        lines = [
            f"Routine: [bold cyan]{d.get('routine_name', '?')}[/]",
            f"Schedule: {d.get('cron_expression', '?')}",
            f"Timezone: {d.get('timezone', '?')}",
            f"Model: {d.get('model', 'sonnet')}",
        ]

        mcp_servers = d.get("mcp_servers", [])
        if mcp_servers:
            lines.append(f"MCP Servers: {', '.join(mcp_servers)}")
            mcp_tools = d.get("mcp_selected_tools", {})
            for srv, tools in mcp_tools.items():
                lines.append(f"  {srv}: {', '.join(tools)}")
        else:
            lines.append("MCP Servers: none")

        lines.append(f"Tools: {', '.join(d.get('allowed_tools', []))}")

        if d.get("docker_enabled"):
            lines.append(
                f"Docker: {d.get('docker_image', 'node:20')} "
                f"(network={d.get('docker_network', 'bridge')})"
            )
        else:
            lines.append("Docker: off")

        env_parts = []
        if d.get("isolated_runs"):
            env_parts.append("isolated")
        if d.get("keep_executions"):
            env_parts.append("keep")
        if d.get("clone_repo"):
            env_parts.append(f"clone={d.get('clone_repo')}")
        lines.append(f"Environment: {', '.join(env_parts) or 'default'}")
        lines.append(f"Setup script: {'yes' if d.get('setup_script_enabled') else 'no'}")

        prompt_preview = d.get("prompt_text", "").strip()
        if prompt_preview:
            preview = prompt_preview[:200] + ("..." if len(prompt_preview) > 200 else "")
            lines.append(f"\nPrompt preview:\n{preview}")

        container.mount(Static("\n".join(lines), id="summary-area", classes="summary-block"))

    def _collect_step_11(self) -> bool:
        self._create_routine()
        return True

    def _create_routine(self) -> None:
        d = self._data
        name = d.get("routine_name", "unnamed")
        routine_dir = ROUTINES_PATH / name
        routine_dir.mkdir(parents=True, exist_ok=True)
        (routine_dir / "env").mkdir(exist_ok=True)
        (routine_dir / "logs").mkdir(exist_ok=True)

        config = self._generate_config()
        with (routine_dir / "config.json").open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        with (routine_dir / "PROMT.md").open("w", encoding="utf-8") as f:
            f.write(d.get("prompt_text", ""))

        if d.get("setup_script_enabled"):
            setup_path = routine_dir / "setup.sh"
            setup_path.write_text(d.get("setup_script", ""), encoding="utf-8")
            setup_path.chmod(setup_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        self.push_screen(SuccessScreen(routine_dir))

    def _generate_config(self) -> dict:
        d = self._data
        task: dict = {
            "job_name": d["routine_name"],
            "schedule": {
                "type": "cron",
                "expression": d["cron_expression"],
            },
        }
        if d.get("setup_script_enabled"):
            task["startup_script"] = "setup.sh"

        model_config: dict = {
            "model": d.get("model", "sonnet"),
            "allowed_tools": d.get("allowed_tools", ["Bash", "Read", "Edit"]),
        }

        mcp_servers = d.get("mcp_servers", [])
        if mcp_servers:
            model_config["mcp_servers"] = mcp_servers
            mcp_tools = d.get("mcp_selected_tools", {})
            if mcp_tools:
                model_config["mcp_selected_tools"] = mcp_tools

        config: dict = {
            "scheduler": {
                "enabled": True,
                "timezone": d.get("timezone", "Europe/Rome"),
                "tasks": [task],
            },
            "model_config": model_config,
        }

        if d.get("docker_enabled"):
            docker: dict = {
                "enabled": True,
                "image": d.get("docker_image", "node:20"),
                "network": d.get("docker_network", "bridge"),
            }
            extra_vols = d.get("docker_extra_volumes", [])
            if extra_vols:
                docker["extra_volumes"] = extra_vols
            config["docker"] = docker

        env_config: dict = {}
        if d.get("isolated_runs"):
            env_config["isolated_runs"] = True
        if d.get("keep_executions"):
            env_config["keep_executions"] = True
        if d.get("clone_repo"):
            env_config["clone_repo"] = d["clone_repo"]
            env_config["clone_branch"] = d.get("clone_branch", "main")
        if env_config:
            config["environment"] = env_config

        return config


class SuccessScreen(ModalScreen):
    CSS = """
    ModalScreen {
        align: center middle;
    }
    .dialog {
        padding: 2 4;
        border: thick $success;
        background: $surface;
        width: 60;
        max-width: 80%;
        height: auto;
    }
    .dialog-title {
        text-style: bold;
        color: $success;
        margin-bottom: 1;
    }
    """

    def __init__(self, routine_dir: Path) -> None:
        super().__init__()
        self.routine_dir = routine_dir

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("Routine created!", classes="dialog-title")
            yield Static(str(self.routine_dir))
            yield Button("Done", variant="success", id="done-btn")

    @on(Button.Pressed, "#done-btn")
    def on_done(self) -> None:
        self.app.exit()


def main() -> None:
    app = CreateRoutineApp()
    app.run()


if __name__ == "__main__":
    main()
