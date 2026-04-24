#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$ROOT_DIR/src"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=13

AUTO_INSTALL_UV=0
SKIP_ONBOARD=0

for arg in "$@"; do
  case "$arg" in
    --install-uv)
      AUTO_INSTALL_UV=1
      ;;
    --no-onboard)
      SKIP_ONBOARD=1
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./bootstrap.sh [--install-uv] [--no-onboard]

Options:
  --install-uv   Install uv automatically if it is missing
  --no-onboard   Only sync dependencies, skip the interactive onboarding flow
  -h, --help     Show this help message
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

require_command() {
  local cmd="$1"
  local message="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$message" >&2
    exit 1
  fi
}

check_python_version() {
  local version_output
  version_output="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

  local major="${version_output%%.*}"
  local minor="${version_output##*.}"

  if (( major < MIN_PYTHON_MAJOR )) || { (( major == MIN_PYTHON_MAJOR )) && (( minor < MIN_PYTHON_MINOR )); }; then
    echo "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required. Found: ${version_output}" >&2
    exit 1
  fi
}

install_uv() {
  require_command curl "curl is required to install uv automatically. Install uv manually: https://docs.astral.sh/uv/"
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  if [ -x "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  require_command uv "uv installation finished, but uv is still not available in PATH. Reopen the shell and run ./bootstrap.sh again."
}

echo "==> Checking system requirements"
require_command python3 "python3 is required. Install Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ and rerun ./bootstrap.sh."
check_python_version

if ! command -v uv >/dev/null 2>&1; then
  if [ "$AUTO_INSTALL_UV" -eq 1 ]; then
    install_uv
  else
    echo "uv is required but was not found." >&2
    echo "Install it from https://docs.astral.sh/uv/ or rerun with ./bootstrap.sh --install-uv" >&2
    exit 1
  fi
fi

echo "==> Syncing Python dependencies"
(cd "$SRC_DIR" && uv sync --reinstall-package routines)

if [ "$SKIP_ONBOARD" -eq 1 ]; then
  echo "==> Dependencies installed. Onboarding skipped."
  echo "Next steps:"
  echo "  cd src && uv run onboard"
  echo "  cd src && uv run -m cli.create_routine"
  echo "  cd src && uv run mcp-server"
  exit 0
fi

echo "==> Starting onboarding"
(cd "$SRC_DIR" && uv run onboard)
