#!/usr/bin/env python3
"""Structured environment check CLI based on Rich."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


@dataclass
class CheckResult:
    name: str
    installed: bool
    status: str
    details: str
    install_help: str


def run_command(*args: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False, ""
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return completed.returncode == 0, output


def detect_os() -> tuple[str, str]:
    system = platform.system()
    if system == "Linux":
        os_release = Path("/etc/os-release")
        if os_release.exists():
            data: dict[str, str] = {}
            for line in os_release.read_text(encoding="utf-8").splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                data[key] = value.strip().strip('"')
            pretty_name = data.get("PRETTY_NAME")
            if pretty_name:
                return system, pretty_name
    return system, platform.platform()


def detect_python_install() -> CheckResult:
    python_bin = shutil.which("python3") or shutil.which("python")
    if python_bin is None:
        return CheckResult(
            name="Python",
            installed=False,
            status="Non installato",
            details="Python non e' nel PATH.",
            install_help=python_install_help(),
        )

    return CheckResult(
        name="Python",
        installed=True,
        status="Installato",
        details=f"{python_bin} | {sys.version.split()[0]}",
        install_help=python_install_help(),
    )


def detect_uv_install() -> CheckResult:
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        return CheckResult(
            name="uv",
            installed=False,
            status="Non installato",
            details="`uv` non e' nel PATH.",
            install_help=uv_install_help(),
        )

    ok, output = run_command("uv", "--version")
    version = output if ok and output else uv_bin
    return CheckResult(
        name="uv",
        installed=True,
        status="Installato",
        details=version,
        install_help=uv_install_help(),
    )


def detect_node_install() -> CheckResult:
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm")
    if node_bin is None or npm_bin is None:
        return CheckResult(
            name="Node.js / npm",
            installed=False,
            status="Non installato",
            details="`node` e/o `npm` non trovati nel PATH.",
            install_help=node_install_help(),
        )

    ok, output = run_command("node", "--version")
    version = output if ok and output else node_bin
    return CheckResult(
        name="Node.js / npm",
        installed=True,
        status="Installato",
        details=f"{version} | npm: {npm_bin}",
        install_help=node_install_help(),
    )


def detect_claude_code_install() -> CheckResult:
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return CheckResult(
            name="Claude Code",
            installed=False,
            status="Non installato",
            details="Comando `claude` non trovato nel PATH.",
            install_help=claude_install_help(),
        )

    ok, output = run_command("claude", "--version")
    version = output if ok and output else claude_bin
    return CheckResult(
        name="Claude Code",
        installed=True,
        status="Installato",
        details=version,
        install_help=claude_install_help(),
    )


def detect_docker_install() -> CheckResult:
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return CheckResult(
            name="Docker",
            installed=False,
            status="Non installato",
            details="Comando `docker` non trovato nel PATH.",
            install_help=docker_install_help(),
        )

    ok, output = run_command("docker", "--version")
    version = output if ok and output else docker_bin
    return CheckResult(
        name="Docker",
        installed=True,
        status="Installato",
        details=version,
        install_help=docker_install_help(),
    )


def detect_docker_activity() -> tuple[str, str]:
    if shutil.which("docker") is None:
        return "Non verificabile", "Docker non e' installato."

    ok, output = run_command("docker", "info")
    if ok:
        return "Attivo", "Il demone Docker risponde correttamente."

    lowered = output.lower()
    if "permission denied" in lowered:
        return "Non accessibile", (
            "Docker e' installato ma l'utente corrente non ha accesso al socket. "
            "Su Linux aggiungi l'utente al gruppo `docker` oppure usa `sudo`."
        )
    if "cannot connect" in lowered or "is the docker daemon running" in lowered:
        return "Non attivo", docker_start_help()
    return "Da verificare", output or "Docker e' installato, ma `docker info` non ha risposto come atteso."


def detect_venv_status() -> tuple[str, str]:
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return "Attivo", f"Ambiente attivo: {virtual_env}"

    if getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        return "Attivo", f"Ambiente attivo: {sys.prefix}"

    return "Non attivo", venv_help()


def current_os_key() -> str:
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    return "linux"


def python_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: usa il package manager. "
            "Debian/Ubuntu `sudo apt install python3 python3-venv`, "
            "Fedora `sudo dnf install python3`, "
            "Arch `sudo pacman -S python`."
        ),
        "macos": (
            "macOS: `brew install python` oppure installer ufficiale da python.org."
        ),
        "windows": (
            "Windows: `winget install Python.Python.3.13` oppure installer ufficiale da python.org. "
            "Durante l'installazione abilita `Add Python to PATH`."
        ),
    }
    return help_map[current_os_key()]


def uv_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`, "
            "poi riapri la shell o ricarica il profilo."
        ),
        "macos": (
            "macOS: `brew install uv` oppure `curl -LsSf https://astral.sh/uv/install.sh | sh`."
        ),
        "windows": (
            "Windows: `winget install astral-sh.uv` oppure `powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"`."
        ),
    }
    return help_map[current_os_key()]


def node_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: installa Node.js LTS. Su Debian/Ubuntu puoi usare i pacchetti NodeSource "
            "oppure il package manager della distro, poi verifica con `node --version` e `npm --version`."
        ),
        "macos": (
            "macOS: `brew install node` oppure installer ufficiale da nodejs.org."
        ),
        "windows": (
            "Windows: `winget install OpenJS.NodeJS.LTS` oppure installer ufficiale da nodejs.org."
        ),
    }
    return help_map[current_os_key()]


def claude_install_help() -> str:
    return (
        "Claude Code: richiede Node.js e npm. Dopo Node, installa con "
        "`npm install -g @anthropic-ai/claude-code`. "
        "Verifica con `claude --version` e poi autentica il tool secondo il tuo setup."
    )


def docker_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: installa Docker Engine dal repository ufficiale della tua distro. "
            "Su Ubuntu/Debian conviene seguire la guida Docker ufficiale, poi "
            "`sudo systemctl enable --now docker` e opzionalmente "
            "`sudo usermod -aG docker $USER`."
        ),
        "macos": (
            "macOS: installa Docker Desktop dal sito Docker oppure con `brew install --cask docker`."
        ),
        "windows": (
            "Windows: installa Docker Desktop dal sito Docker o con "
            "`winget install Docker.DockerDesktop`. WSL2 deve essere attivo."
        ),
    }
    return help_map[current_os_key()]


def docker_start_help() -> str:
    help_map = {
        "linux": (
            "Docker e' installato ma non attivo. Avvio tipico Linux: "
            "`sudo systemctl start docker` e, se serve all'avvio, "
            "`sudo systemctl enable docker`."
        ),
        "macos": (
            "Docker e' installato ma non attivo. Apri Docker Desktop e attendi che il motore risulti avviato."
        ),
        "windows": (
            "Docker e' installato ma non attivo. Avvia Docker Desktop e verifica che WSL2/virtualizzazione siano abilitate."
        ),
    }
    return help_map[current_os_key()]


def venv_help() -> str:
    return (
        "Virtualenv non attivo. Crea l'ambiente con `uv venv` oppure "
        "`python -m venv .venv`, poi attivalo con "
        "`source .venv/bin/activate` su Linux/macOS o "
        "`.venv\\Scripts\\activate` su Windows."
    )


def build_summary_table(results: list[CheckResult], docker_runtime: tuple[str, str], venv_status: tuple[str, str]) -> Table:
    table = Table(title="Stato Ambiente", expand=True)
    table.add_column("Componente", style="cyan", no_wrap=True)
    table.add_column("Stato", style="bold")
    table.add_column("Dettagli")

    for result in results:
        table.add_row(result.name, result.status, result.details)

    table.add_row("Docker Engine", docker_runtime[0], docker_runtime[1])
    table.add_row("Virtualenv", venv_status[0], venv_status[1])
    return table


def main() -> None:
    os_name, os_description = detect_os()
    results = [
        detect_node_install(),
        detect_claude_code_install(),
        detect_docker_install(),
        detect_uv_install(),
        detect_python_install(),
    ]
    docker_runtime = detect_docker_activity()
    venv_status = detect_venv_status()

    console.print(
        Panel.fit(
            f"[bold]Sistema rilevato[/bold]\n{os_name} | {os_description}",
            title="Environment Check",
            border_style="blue",
        )
    )
    console.print(build_summary_table(results, docker_runtime, venv_status))

    for result in results:
        if result.installed:
            title = f"{result.name}: ok"
            body = result.details
        else:
            title = f"{result.name}: come installare"
            body = result.install_help
        console.print(Panel(body, title=title, expand=True))

    if docker_runtime[0] != "Attivo":
        console.print(Panel(docker_runtime[1], title="Docker: attivazione", expand=True))

    if venv_status[0] != "Attivo":
        console.print(Panel(venv_status[1], title="Python virtualenv", expand=True))


if __name__ == "__main__":
    main()
