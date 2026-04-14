#!/usr/bin/env bash
# Claude Code dotfiles installer
# Usage: bash setup.sh
#
# Copies commands/, templates/, and scripts into ~/.claude/
# Optionally installs Codex global skills into ~/.codex/skills with --codex.
# Existing files are NOT overwritten (use -f to force).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME:-$USERPROFILE}/.claude"
CODEX_DIR="${HOME:-$USERPROFILE}/.codex"
FORCE=false
STATUSLINE=false
CODEX=false

for arg in "$@"; do
    case "$arg" in
        -f)           FORCE=true ;;
        --statusline) STATUSLINE=true ;;
        --codex)      CODEX=true ;;
    esac
done

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

# 2. Templates (used by init-project.ps1)
echo "[templates]"
copy_tree "$SCRIPT_DIR/templates" "$CLAUDE_DIR/templates"
echo ""

# 3. Scripts (e.g. init-project.ps1)
echo "[scripts]"
copy_tree "$SCRIPT_DIR/scripts" "$CLAUDE_DIR/scripts"
echo ""

if [[ "$STATUSLINE" == "true" ]]; then
    echo "[statusline]"
    if [[ "$FORCE" == "true" ]]; then
        bash "$SCRIPT_DIR/setup-statusline.sh" -f 2>&1 | grep -E '^\s+(SKIP|COPY|SET)\s' || true
    else
        bash "$SCRIPT_DIR/setup-statusline.sh" 2>&1 | grep -E '^\s+(SKIP|COPY|SET)\s' || true
    fi
    echo ""
fi

if [[ "$CODEX" == "true" ]]; then
    echo "[codex-skills]"
    copy_tree "$SCRIPT_DIR/codex/skills" "$CODEX_DIR/skills"
    echo ""
fi

echo "=== Done ==="
echo ""
echo "Available commands:"
echo "  /init-project    Set up a new project with Claude Code × Codex workflow"
echo "  /update-workflow Refresh workflow commands/agents for an existing project"
echo "  /update-skills   Compatibility alias for /update-workflow"
echo ""
echo "Options:"
echo "  -f               Overwrite existing files"
echo "  --statusline     Also set up the custom status line"
echo "  --codex          Also install Codex global skills into ~/.codex/skills"
