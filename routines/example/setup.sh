#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="$(cd "$(dirname "$0")/env" && pwd)"

# Initialize data file if missing
if [ ! -f "$ENV_DIR/health-check-data.txt" ]; then
  echo "Nessun check precedente" > "$ENV_DIR/health-check-data.txt"
fi

# Cleanup old reports (keep last 10)
cd "$ENV_DIR"
ls -t health-report-*.txt 2>/dev/null | tail -n +11 | xargs -r rm --

echo "Setup completato — env: $ENV_DIR"
