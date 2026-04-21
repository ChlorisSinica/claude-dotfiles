#!/usr/bin/env bash
# Thin compatibility wrapper. The canonical installer is scripts/setup.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FORWARD_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --statusline)
            FORWARD_ARGS+=("$arg")
            ;;
        *)
            FORWARD_ARGS+=("$arg")
            ;;
    esac
done

resolve_python() {
    if command -v python3 >/dev/null 2>&1; then
        printf '%s\n' "python3"
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        printf '%s\n' "python"
        return 0
    fi
    if command -v py >/dev/null 2>&1; then
        printf '%s\n' "py -3"
        return 0
    fi
    return 1
}

PYTHON_LAUNCHER="$(resolve_python || true)"
if [[ -z "$PYTHON_LAUNCHER" ]]; then
    echo "ERROR: Python 3.11+ launcher not found. Use scripts/setup.py directly with python, python3, or py -3." >&2
    exit 1
fi

if [[ "$PYTHON_LAUNCHER" == "py -3" ]]; then
    py -3 "$SCRIPT_DIR/scripts/setup.py" "${FORWARD_ARGS[@]}"
else
    "$PYTHON_LAUNCHER" "$SCRIPT_DIR/scripts/setup.py" "${FORWARD_ARGS[@]}"
fi
