#!/usr/bin/env bash
# Compatibility wrapper. The single implementation lives in init-project.ps1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PS1_PATH="$SCRIPT_DIR/init-project.ps1"

if command -v pwsh >/dev/null 2>&1; then
    exec pwsh -NoProfile -ExecutionPolicy Bypass -File "$PS1_PATH" "$@"
fi

if command -v powershell >/dev/null 2>&1; then
    exec powershell -NoProfile -ExecutionPolicy Bypass -File "$PS1_PATH" "$@"
fi

echo "ERROR: PowerShell was not found. Use scripts/init-project.ps1 directly on Windows." >&2
exit 1
