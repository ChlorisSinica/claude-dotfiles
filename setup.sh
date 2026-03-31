#!/usr/bin/env bash
# Claude Code dotfiles installer
# Usage: bash setup.sh
#
# Copies commands/, templates/, and dotfiles/ into ~/.claude/
# Existing files are NOT overwritten (use -f to force).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME:-$USERPROFILE}/.claude"
FORCE=false

if [[ "${1:-}" == "-f" ]]; then
    FORCE=true
fi

copy_tree() {
    local src="$1" dest="$2"
    find "$src" -type f | while read -r file; do
        rel="${file#"$src"/}"
        target="$dest/$rel"
        if [[ -f "$target" && "$FORCE" == "false" ]]; then
            echo "  SKIP  $rel (already exists)"
        else
            mkdir -p "$(dirname "$target")"
            cp "$file" "$target"
            echo "  COPY  $rel"
        fi
    done
}

echo "=== Claude Code dotfiles setup ==="
echo "Source:  $SCRIPT_DIR"
echo "Target:  $CLAUDE_DIR"
echo ""

# 1. Global commands (e.g. /init-project)
echo "[commands]"
copy_tree "$SCRIPT_DIR/commands" "$CLAUDE_DIR/commands"
echo ""

# 2. Templates (used by /init-project)
echo "[templates]"
copy_tree "$SCRIPT_DIR/templates" "$CLAUDE_DIR/templates"
echo ""

# 3. Dotfiles (files placed directly into ~/.claude/)
echo "[dotfiles]"
copy_tree "$SCRIPT_DIR/dotfiles" "$CLAUDE_DIR"
echo ""

# 4. Statusline config in settings.json
echo "[statusline]"
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
echo ""
echo "Available commands:"
echo "  /init-project    Set up a new project with Claude Code × Codex workflow"
echo ""
echo "To overwrite existing files, run: bash setup.sh -f"
