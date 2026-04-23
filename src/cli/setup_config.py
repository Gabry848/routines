#!/usr/bin/env python3
"""Interactive setup for project-local Claude runtime configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from scheduler.constants import LOCAL_CLAUDE_JSON_PATH, LOCAL_CLAUDE_SETTINGS_PATH, LOCAL_CONFIG_PATH
from scheduler.project_config import (
    ensure_local_config_dirs,
    load_local_claude_json,
    load_local_claude_settings,
    save_local_claude_json,
    save_local_claude_settings,
)


console = Console()

HOME_CLAUDE_JSON_PATH = Path.home() / ".claude.json"
HOME_CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
PROJECT_MCP_JSON_PATH = Path(__file__).resolve().parent.parent.parent / ".mcp.json"


def prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = console.input(f"{question} {suffix} ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes", "s", "si"}:
            return True
        if value in {"n", "no"}:
            return False
        console.print("[red]Risposta non valida.[/red]")


def prompt_text(question: str, default: str = "", secret: bool = False) -> str:
    rendered_default = f" [{default}]" if default else ""
    while True:
        value = console.input(f"{question}{rendered_default}: ", password=secret).strip()
        if value:
            return value
        if default:
            return default
        console.print("[red]Valore obbligatorio.[/red]")


def prompt_optional_text(question: str, default: str = "", secret: bool = False) -> str:
    rendered_default = f" [{default}]" if default else ""
    value = console.input(f"{question}{rendered_default}: ", password=secret).strip()
    return value or default


def prompt_json(question: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    console.print(question)
    console.print("Incolla JSON su una riga. Lascia vuoto per usare il default.")
    default_text = json.dumps(default, indent=2) if default else ""
    if default_text:
        console.print(Panel(default_text, title="Default", expand=False))
    while True:
        value = console.input("JSON: ").strip()
        if not value:
            return default or {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            console.print(f"[red]JSON non valido:[/red] {exc}")
            continue
        if not isinstance(parsed, dict):
            console.print("[red]Serve un oggetto JSON.[/red]")
            continue
        return parsed


def load_json_dict(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def build_settings_from_import() -> dict[str, Any]:
    imported = load_json_dict(HOME_CLAUDE_SETTINGS_PATH)
    if not imported:
        console.print(
            f"[yellow]Nessun file importabile trovato in {HOME_CLAUDE_SETTINGS_PATH}.[/yellow]"
        )
        return {}

    console.print(f"Import da [bold]{HOME_CLAUDE_SETTINGS_PATH}[/bold].")
    return imported


def build_settings_manually(existing: dict[str, Any]) -> dict[str, Any]:
    env_defaults = existing.get("env", {}) if isinstance(existing.get("env"), dict) else {}

    env = {
        "ANTHROPIC_AUTH_TOKEN": prompt_text(
            "ANTHROPIC_AUTH_TOKEN",
            default=str(env_defaults.get("ANTHROPIC_AUTH_TOKEN", "")),
            secret=True,
        ),
        "ANTHROPIC_BASE_URL": prompt_optional_text(
            "ANTHROPIC_BASE_URL",
            default=str(env_defaults.get("ANTHROPIC_BASE_URL", "")),
        ),
        "API_TIMEOUT_MS": prompt_optional_text(
            "API_TIMEOUT_MS",
            default=str(env_defaults.get("API_TIMEOUT_MS", "3000000")),
        ),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": prompt_optional_text(
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
            default=str(env_defaults.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")),
        ),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": prompt_optional_text(
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            default=str(env_defaults.get("ANTHROPIC_DEFAULT_HAIKU_MODEL", "")),
        ),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": prompt_optional_text(
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            default=str(env_defaults.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "")),
        ),
        "ANTHROPIC_DEFAULT_OPUS_MODEL": prompt_optional_text(
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            default=str(env_defaults.get("ANTHROPIC_DEFAULT_OPUS_MODEL", "")),
        ),
    }

    settings: dict[str, Any] = {"env": {k: v for k, v in env.items() if v}}

    if prompt_yes_no("Vuoi configurare enabledPlugins?", default=bool(existing.get("enabledPlugins"))):
        settings["enabledPlugins"] = prompt_json(
            "Inserisci enabledPlugins come oggetto JSON.",
            default=existing.get("enabledPlugins") if isinstance(existing.get("enabledPlugins"), dict) else {},
        )

    if prompt_yes_no(
        "Vuoi configurare extraKnownMarketplaces?",
        default=bool(existing.get("extraKnownMarketplaces")),
    ):
        settings["extraKnownMarketplaces"] = prompt_json(
            "Inserisci extraKnownMarketplaces come oggetto JSON.",
            default=existing.get("extraKnownMarketplaces")
            if isinstance(existing.get("extraKnownMarketplaces"), dict)
            else {},
        )

    if prompt_yes_no("Vuoi salvare mcpServers dentro settings.json?", default=False):
        settings["mcpServers"] = prompt_json(
            "Inserisci mcpServers come oggetto JSON.",
            default=existing.get("mcpServers") if isinstance(existing.get("mcpServers"), dict) else {},
        )

    return settings


def choose_claude_json_source(existing: dict[str, Any]) -> dict[str, Any]:
    console.print("")
    console.print("[bold]Configurazione MCP / claude.json[/bold]")

    if prompt_yes_no("Vuoi copiare ~/.claude.json nel progetto?", default=HOME_CLAUDE_JSON_PATH.exists()):
        imported = load_json_dict(HOME_CLAUDE_JSON_PATH)
        if imported:
            console.print(f"Copiato contenuto da [bold]{HOME_CLAUDE_JSON_PATH}[/bold].")
            return imported
        console.print(f"[yellow]Nessun file valido in {HOME_CLAUDE_JSON_PATH}.[/yellow]")

    if prompt_yes_no("Vuoi importare mcpServers da .mcp.json del progetto?", default=PROJECT_MCP_JSON_PATH.exists()):
        imported = load_json_dict(PROJECT_MCP_JSON_PATH)
        if imported:
            console.print(f"Importato contenuto da [bold]{PROJECT_MCP_JSON_PATH}[/bold].")
            return imported
        console.print(f"[yellow]Nessun file valido in {PROJECT_MCP_JSON_PATH}.[/yellow]")

    if prompt_yes_no("Vuoi inserire manualmente il contenuto di claude.json?", default=bool(existing)):
        return prompt_json(
            "Inserisci l'intero contenuto di claude.json come oggetto JSON.",
            default=existing,
        )

    return {}


def run_setup(show_intro: bool = True) -> None:
    if show_intro:
        console.print(
        Panel(
            "Questa procedura crea una configurazione locale in `.config/routines`.\n"
            "Dopo il setup il programma usera' solo questi file e non leggera' `~/.claude*`.",
            title="Routine Setup",
            expand=False,
        )
        )

    ensure_local_config_dirs()

    existing_settings = load_local_claude_settings()
    existing_claude_json = load_local_claude_json()

    use_installed = prompt_yes_no(
        "Vuoi usare come base la configurazione di Claude Code installato?",
        default=HOME_CLAUDE_SETTINGS_PATH.exists(),
    )

    if use_installed:
        settings = build_settings_from_import()
        if not settings:
            settings = build_settings_manually(existing_settings)
    else:
        settings = build_settings_manually(existing_settings)

    if prompt_yes_no("Vuoi rivedere manualmente il JSON finale di settings.json?", default=False):
        settings = prompt_json(
            "Inserisci l'intero contenuto finale di settings.json come oggetto JSON.",
            default=settings,
        )

    claude_json = choose_claude_json_source(existing_claude_json)

    save_local_claude_settings(settings)
    save_local_claude_json(claude_json)

    console.print("")
    console.print("[green]Configurazione salvata.[/green]")
    console.print(f"- settings: {LOCAL_CLAUDE_SETTINGS_PATH}")
    console.print(f"- claude.json: {LOCAL_CLAUDE_JSON_PATH}")
    console.print(f"- root config: {LOCAL_CONFIG_PATH}")


def main() -> None:
    run_setup(show_intro=True)


if __name__ == "__main__":
    main()
