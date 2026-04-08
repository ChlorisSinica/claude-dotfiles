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

# 2. Templates (used by init-project.sh)
echo "[templates]"
copy_tree "$SCRIPT_DIR/templates" "$CLAUDE_DIR/templates"
echo ""

# 3. Scripts (e.g. init-project.sh)
echo "[scripts]"
copy_tree "$SCRIPT_DIR/scripts" "$CLAUDE_DIR/scripts"
echo ""

# 4. Statusline
echo "[statusline]"
if [[ "$FORCE" == "true" ]]; then
    bash "$SCRIPT_DIR/setup-statusline.sh" -f 2>&1 | grep -E '^\s+(SKIP|COPY|SET)\s' || true
else
    bash "$SCRIPT_DIR/setup-statusline.sh" 2>&1 | grep -E '^\s+(SKIP|COPY|SET)\s' || true
fi
echo ""

echo "=== Done ==="
echo ""
echo "Available commands:"
echo "  /init-project    Set up a new project with Claude Code × Codex workflow"
echo ""
echo "To overwrite existing files, run: bash setup.sh -f"
