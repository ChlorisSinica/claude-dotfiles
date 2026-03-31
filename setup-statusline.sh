#!/usr/bin/env bash
# Statusline installer for Claude Code
# Usage: bash setup-statusline.sh [-f]
#
# Installs statusline.py into ~/.claude/ and configures settings.json.
# Existing statusline.py is NOT overwritten (use -f to force).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME:-$USERPROFILE}/.claude"
FORCE=false

if [[ "${1:-}" == "-f" ]]; then
    FORCE=true
fi

echo "=== Statusline setup ==="
echo ""

# 1. Copy statusline.py
SRC="$SCRIPT_DIR/dotfiles/statusline.py"
DEST="$CLAUDE_DIR/statusline.py"
if [[ -f "$DEST" && "$FORCE" == "false" ]]; then
    echo "  SKIP  statusline.py (already exists)"
else
    mkdir -p "$CLAUDE_DIR"
    cp "$SRC" "$DEST"
    echo "  COPY  statusline.py"
fi

# 2. Configure settings.json
echo ""
SETTINGS="$CLAUDE_DIR/settings.json"
python -c "
import json, sys, os
path = sys.argv[1]
data = {}
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
desired = {'type': 'command', 'command': 'python ~/.claude/statusline.py'}
if data.get('statusLine') == desired:
    print('  SKIP  statusLine (already configured)')
else:
    data['statusLine'] = desired
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('  SET   statusLine -> python ~/.claude/statusline.py')
" "$SETTINGS"

echo ""
echo "=== Done ==="
echo "Restart Claude Code to activate the new statusline."
