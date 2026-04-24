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
            status="Not installed",
            details="Python is not available in PATH.",
            install_help=python_install_help(),
        )

    return CheckResult(
        name="Python",
        installed=True,
        status="Installed",
        details=f"{python_bin} | {sys.version.split()[0]}",
        install_help=python_install_help(),
    )


def detect_uv_install() -> CheckResult:
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        return CheckResult(
            name="uv",
            installed=False,
            status="Not installed",
            details="`uv` is not available in PATH.",
            install_help=uv_install_help(),
        )

    ok, output = run_command("uv", "--version")
    version = output if ok and output else uv_bin
    return CheckResult(
        name="uv",
        installed=True,
        status="Installed",
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
            status="Not installed",
            details="`node` and/or `npm` were not found in PATH.",
            install_help=node_install_help(),
        )

    ok, output = run_command("node", "--version")
    version = output if ok and output else node_bin
    return CheckResult(
        name="Node.js / npm",
        installed=True,
        status="Installed",
        details=f"{version} | npm: {npm_bin}",
        install_help=node_install_help(),
    )


def detect_claude_code_install() -> CheckResult:
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return CheckResult(
            name="Claude Code",
            installed=False,
            status="Not installed",
            details="`claude` was not found in PATH.",
            install_help=claude_install_help(),
        )

    ok, output = run_command("claude", "--version")
    version = output if ok and output else claude_bin
    return CheckResult(
        name="Claude Code",
        installed=True,
        status="Installed",
        details=version,
        install_help=claude_install_help(),
    )


def detect_docker_install() -> CheckResult:
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return CheckResult(
            name="Docker",
            installed=False,
            status="Not installed",
            details="`docker` was not found in PATH.",
            install_help=docker_install_help(),
        )

    ok, output = run_command("docker", "--version")
    version = output if ok and output else docker_bin
    return CheckResult(
        name="Docker",
        installed=True,
        status="Installed",
        details=version,
        install_help=docker_install_help(),
    )


def detect_docker_activity() -> tuple[str, str]:
    if shutil.which("docker") is None:
        return "Unavailable", "Docker is not installed."

    ok, output = run_command("docker", "info")
    if ok:
        return "Active", "The Docker daemon is responding correctly."

    lowered = output.lower()
    if "permission denied" in lowered:
        return "Permission denied", (
            "Docker is installed but the current user cannot access the socket. "
            "On Linux, add the user to the `docker` group or use `sudo`."
        )
    if "cannot connect" in lowered or "is the docker daemon running" in lowered:
        return "Not active", docker_start_help()
    return "Needs attention", output or "Docker is installed, but `docker info` did not respond as expected."


def detect_venv_status() -> tuple[str, str]:
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return "Active", f"Active environment: {virtual_env}"

    if getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        return "Active", f"Active environment: {sys.prefix}"

    return "Not active", venv_help()


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
            "Linux: use your package manager. "
            "Debian/Ubuntu `sudo apt install python3 python3-venv`, "
            "Fedora `sudo dnf install python3`, "
            "Arch `sudo pacman -S python`."
        ),
        "macos": (
            "macOS: `brew install python` or the official installer from python.org."
        ),
        "windows": (
            "Windows: `winget install Python.Python.3.13` or the official installer from python.org. "
            "Enable `Add Python to PATH` during installation."
        ),
    }
    return help_map[current_os_key()]


def uv_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`, "
            "then reopen the shell or reload your profile."
        ),
        "macos": (
            "macOS: `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`."
        ),
        "windows": (
            "Windows: `winget install astral-sh.uv` or `powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"`."
        ),
    }
    return help_map[current_os_key()]


def node_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: install Node.js LTS. On Debian/Ubuntu you can use NodeSource packages "
            "or the distro package manager, then verify with `node --version` and `npm --version`."
        ),
        "macos": (
            "macOS: `brew install node` or the official installer from nodejs.org."
        ),
        "windows": (
            "Windows: `winget install OpenJS.NodeJS.LTS` or the official installer from nodejs.org."
        ),
    }
    return help_map[current_os_key()]


def claude_install_help() -> str:
    return (
        "Claude Code requires Node.js and npm. After Node, install it with "
        "`npm install -g @anthropic-ai/claude-code`. "
        "Verify with `claude --version`, then authenticate the tool for your setup."
    )


def docker_install_help() -> str:
    help_map = {
        "linux": (
            "Linux: install Docker Engine from the official repository for your distro. "
            "On Ubuntu/Debian, the official Docker guide is usually the best path, then run "
            "`sudo systemctl enable --now docker` and optionally "
            "`sudo usermod -aG docker $USER`."
        ),
        "macos": (
            "macOS: install Docker Desktop from docker.com or with `brew install --cask docker`."
        ),
        "windows": (
            "Windows: install Docker Desktop from docker.com or with "
            "`winget install Docker.DockerDesktop`. WSL2 must be enabled."
        ),
    }
    return help_map[current_os_key()]


def docker_start_help() -> str:
    help_map = {
        "linux": (
            "Docker is installed but not active. Typical Linux startup: "
            "`sudo systemctl start docker` and, if needed at boot, "
            "`sudo systemctl enable docker`."
        ),
        "macos": (
            "Docker is installed but not active. Open Docker Desktop and wait for the engine to start."
        ),
        "windows": (
            "Docker is installed but not active. Start Docker Desktop and verify that WSL2/virtualization is enabled."
        ),
    }
    return help_map[current_os_key()]


def venv_help() -> str:
    return (
        "Virtualenv is not active. Create it with `uv venv` or "
        "`python -m venv .venv`, then activate it with "
        "`source .venv/bin/activate` on Linux/macOS or "
        "`.venv\\Scripts\\activate` on Windows."
    )


def build_summary_table(results: list[CheckResult], docker_runtime: tuple[str, str], venv_status: tuple[str, str]) -> Table:
    table = Table(title="Environment Status", expand=True)
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Details")

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
            f"[bold]Detected system[/bold]\n{os_name} | {os_description}",
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
            title = f"{result.name}: install help"
            body = result.install_help
        console.print(Panel(body, title=title, expand=True))

    if docker_runtime[0] != "Active":
        console.print(Panel(docker_runtime[1], title="Docker: activation", expand=True))

    if venv_status[0] != "Active":
        console.print(Panel(venv_status[1], title="Python virtualenv", expand=True))


if __name__ == "__main__":
    main()
