#!/usr/bin/env python3
"""Project onboarding CLI."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel

from cli import env_check, setup_config


console = Console()


@dataclass
class InstallPlan:
    command: str
    note: str | None = None


def prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        answer = console.input(f"{question} {suffix} ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes", "s", "si"}:
            return True
        if answer in {"n", "no"}:
            return False
        console.print("[red]Risposta non valida.[/red]")


def choose_install_plan(name: str) -> InstallPlan | None:
    system = platform.system()

    if name == "Python":
        if system == "Linux":
            if shutil.which("apt-get"):
                return InstallPlan("sudo apt-get update && sudo apt-get install -y python3 python3-venv")
            if shutil.which("dnf"):
                return InstallPlan("sudo dnf install -y python3")
            if shutil.which("pacman"):
                return InstallPlan("sudo pacman -S --noconfirm python")
        if system == "Darwin" and shutil.which("brew"):
            return InstallPlan("brew install python")
        if system == "Windows":
            return InstallPlan("winget install Python.Python.3.13")
        return None

    if name == "uv":
        if system in {"Linux", "Darwin"}:
            return InstallPlan("curl -LsSf https://astral.sh/uv/install.sh | sh")
        if system == "Windows":
            return InstallPlan('powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"')
        return None

    if name == "Node.js / npm":
        if system == "Linux":
            if shutil.which("apt-get"):
                return InstallPlan("sudo apt-get update && sudo apt-get install -y nodejs npm")
            if shutil.which("dnf"):
                return InstallPlan("sudo dnf install -y nodejs npm")
            if shutil.which("pacman"):
                return InstallPlan("sudo pacman -S --noconfirm nodejs npm")
        if system == "Darwin" and shutil.which("brew"):
            return InstallPlan("brew install node")
        if system == "Windows":
            return InstallPlan("winget install OpenJS.NodeJS.LTS")
        return None

    if name == "Claude Code":
        return InstallPlan(
            "npm install -g @anthropic-ai/claude-code",
            note="Richiede Node.js e npm gia' funzionanti.",
        )

    if name == "Docker":
        if system == "Darwin" and shutil.which("brew"):
            return InstallPlan("brew install --cask docker")
        if system == "Windows":
            return InstallPlan("winget install Docker.DockerDesktop")
        return None

    return None


def run_shell_command(command: str) -> bool:
    console.print(f"[cyan]$ {command}[/cyan]")
    completed = subprocess.run(command, shell=True, check=False)
    return completed.returncode == 0


def render_intro() -> None:
    console.print("")
    console.print(
        Panel.fit(
            "Routines onboard\n\n"
            "- Configura l'ambiente locale del progetto\n"
            "- Controlla dipendenze una per volta\n"
            "- Ti propone installazioni automatiche quando possibile\n"
            "- Salva la config Claude/MCP in `.config/routines`\n\n"
            "Disclaimer\n"
            "- Il progetto puo' leggere file locali, usare tool e lanciare processi.\n"
            "- Mantieni token e credenziali sotto il tuo controllo.\n"
            "- Se abiliti Docker o plugin MCP, verifica bene cosa stai esponendo.",
            title="Onboarding",
            border_style="blue",
        )
    )


def render_system_info() -> None:
    os_name, os_description = env_check.detect_os()
    console.print("")
    console.print(f"1. Sistema: [bold]{os_name}[/bold] | {os_description}")


def check_component(detector: callable) -> env_check.CheckResult:
    result = detector()
    status = "ok" if result.installed else "mancante"
    color = "green" if result.installed else "yellow"
    console.print("")
    console.print(f"2. [bold]{result.name}[/bold]")
    console.print(f"   Stato: [{color}]{status}[/{color}]")
    console.print(f"   Dettagli: {result.details}")
    return result


def handle_missing_component(result: env_check.CheckResult) -> None:
    plan = choose_install_plan(result.name)

    if plan is None:
        console.print("   Installazione automatica non disponibile.")
        console.print(f"   Suggerimento: {result.install_help}")
        return

    if plan.note:
        console.print(f"   Nota: {plan.note}")

    console.print(f"   Comando proposto: `{plan.command}`")
    if not prompt_yes_no(f"   Vuoi provare a installare {result.name} adesso?", default=False):
        return

    ok = run_shell_command(plan.command)
    if ok:
        console.print(f"   [green]{result.name} installato o comando completato.[/green]")
    else:
        console.print("   [red]Installazione non riuscita.[/red]")
        console.print(f"   Suggerimento: {result.install_help}")


def check_docker_runtime() -> None:
    console.print("")
    console.print("3. [bold]Docker Engine[/bold]")
    status, details = env_check.detect_docker_activity()
    color = "green" if status == "Attivo" else "yellow"
    console.print(f"   Stato: [{color}]{status}[/{color}]")
    console.print(f"   Dettagli: {details}")

    if status == "Non attivo" and platform.system() == "Linux" and shutil.which("systemctl"):
        command = "sudo systemctl start docker"
        console.print(f"   Comando proposto: `{command}`")
        if prompt_yes_no("   Vuoi provare ad avviare Docker adesso?", default=False):
            if run_shell_command(command):
                console.print("   [green]Comando eseguito.[/green]")
            else:
                console.print("   [red]Avvio Docker non riuscito.[/red]")


def check_virtualenv() -> None:
    console.print("")
    console.print("4. [bold]Virtualenv[/bold]")
    status, details = env_check.detect_venv_status()
    color = "green" if status == "Attivo" else "yellow"
    console.print(f"   Stato: [{color}]{status}[/{color}]")
    console.print(f"   Dettagli: {details}")


def run_dependency_checks() -> None:
    detectors = [
        env_check.detect_python_install,
        env_check.detect_uv_install,
        env_check.detect_node_install,
        env_check.detect_claude_code_install,
        env_check.detect_docker_install,
    ]

    for detector in detectors:
        result = check_component(detector)
        if not result.installed:
            handle_missing_component(result)

    check_docker_runtime()
    check_virtualenv()


def main() -> None:
    render_intro()
    if not prompt_yes_no(
        "Confermi di voler continuare con il setup locale del progetto?",
        default=True,
    ):
        console.print("Setup annullato.")
        return

    render_system_info()
    run_dependency_checks()

    console.print("")
    console.print("5. [bold]Configurazione Claude[/bold]")
    setup_config.run_setup(show_intro=False)

    console.print("")
    console.print("[green]Onboarding completato.[/green]")
    console.print("Avvio consigliato: `uv run -m cli.create_routine` per generare le routine iniziali.")


if __name__ == "__main__":
    main()
