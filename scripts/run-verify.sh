#!/usr/bin/env bash
set -uo pipefail

VERIFY_CMD="python -m pytest --tb=short -q"
VERIFY_SHELL="bash"
LOG_DIR=".agents/logs/verify"

mkdir -p "$LOG_DIR/history"

timestamp="$(date +%Y%m%d-%H%M%S)"
started_at="$(date -Iseconds)"
log_path="$LOG_DIR/history/${timestamp}-verify.log"
status_path="$LOG_DIR/history/${timestamp}-status.json"
latest_log="$LOG_DIR/latest.log"
latest_status="$LOG_DIR/latest.status.json"

json_escape() {
    awk -v s="$1" 'BEGIN {
        gsub(/\\/,"\\\\",s)
        gsub(/"/,"\\\"",s)
        printf "%s", s
    }'
}

exit_code=0

if [[ "$VERIFY_SHELL" == "powershell" ]]; then
    if command -v pwsh >/dev/null 2>&1; then
        pwsh -NoProfile -ExecutionPolicy Bypass -Command "$VERIFY_CMD" 2>&1 | tee "$log_path"
        exit_code=${PIPESTATUS[0]}
    elif command -v powershell >/dev/null 2>&1; then
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$VERIFY_CMD" 2>&1 | tee "$log_path"
        exit_code=${PIPESTATUS[0]}
    else
        printf '%s\n' 'ERROR: PowerShell was not found but VERIFY_SHELL=powershell.' | tee "$log_path"
        exit_code=127
    fi
else
    bash -lc "$VERIFY_CMD" 2>&1 | tee "$log_path"
    exit_code=${PIPESTATUS[0]}
fi

finished_at="$(date -Iseconds)"
escaped_command="$(json_escape "$VERIFY_CMD")"
escaped_log_path="$(json_escape "$log_path")"

cat > "$status_path" <<EOF
{
  "ok": $([[ "$exit_code" -eq 0 ]] && echo true || echo false),
  "command": "$escaped_command",
  "exit_code": $exit_code,
  "started_at": "$started_at",
  "finished_at": "$finished_at",
  "log_path": "$escaped_log_path"
}
EOF

cp "$log_path" "$latest_log"
cp "$status_path" "$latest_status"

exit "$exit_code"