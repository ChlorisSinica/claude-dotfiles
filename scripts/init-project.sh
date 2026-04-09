#!/usr/bin/env bash
# init-project.sh
# Usage: bash ~/.claude/scripts/init-project.sh <preset> [-f]
#
# Copies .claude/ templates into the current directory and substitutes
# {{LANG}}, {{VERIFY_CMD}}, {{LANG_RULES}} placeholders.
# Existing files are NOT overwritten unless -f is specified.

set -euo pipefail

PRESET=""
FORCE=false

for arg in "$@"; do
    case "$arg" in
        -f) FORCE=true ;;
        *)  PRESET="$arg" ;;
    esac
done

if [[ -z "$PRESET" ]]; then
    echo "ERROR: preset name required" >&2
    echo "Usage: bash ~/.claude/scripts/init-project.sh <preset> [-f]" >&2
    echo "Presets: python, python-pytorch, typescript, rust, ahk, ahk-v2, cpp-msvc" >&2
    exit 1
fi

TEMPLATE_DIR="${HOME}/.claude/templates/project-init/.claude"
PRESET_FILE="${HOME}/.claude/templates/project-init/presets.json"
DEST_DIR="$(pwd)/.claude"

if [[ ! -d "$TEMPLATE_DIR" ]]; then
    echo "ERROR: Template not found: $TEMPLATE_DIR" >&2
    echo "Run: bash ~/claude-dotfiles/setup.sh" >&2
    exit 1
fi

if [[ ! -f "$PRESET_FILE" ]]; then
    echo "ERROR: presets.json not found: $PRESET_FILE" >&2
    exit 1
fi

echo "=== init-project: $PRESET ==="
echo "Dest: $DEST_DIR"
echo ""

# Convert Git Bash POSIX paths (/c/Users/...) to Windows paths (C:/Users/...)
to_win() { echo "$1" | sed 's|^/\([a-z]\)/|\1:/|'; }
TEMPLATE_DIR_PY=$(to_win "$TEMPLATE_DIR")
PRESET_FILE_PY=$(to_win "$PRESET_FILE")
DEST_DIR_PY=$(to_win "$DEST_DIR")

# Copy files and substitute placeholders via Python
if python3 -c "" 2>/dev/null; then
    PYTHON=python3
elif python -c "" 2>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python not found. Install Python 3 to use this script." >&2
    exit 1
fi
"$PYTHON" - "$PRESET" "$TEMPLATE_DIR_PY" "$DEST_DIR_PY" "$PRESET_FILE_PY" "$FORCE" <<'PYEOF'
import sys, json, os

preset_name, template_dir, dest_dir, preset_file, force_str = sys.argv[1:6]
force = force_str == "true"

with open(preset_file, encoding='utf-8') as f:
    presets = json.load(f)

if preset_name not in presets:
    print(f"ERROR: Unknown preset '{preset_name}'", file=sys.stderr)
    print(f"Available: {', '.join(presets.keys())}", file=sys.stderr)
    sys.exit(1)

p = presets[preset_name]

def substitute(content):
    content = content.replace('{{LANG}}',       p.get('LANG', ''))
    content = content.replace('{{VERIFY_CMD}}', p.get('VERIFY_CMD', ''))
    content = content.replace('{{LANG_RULES}}', p.get('LANG_RULES', ''))
    return content

for root, dirs, files in os.walk(template_dir):
    for fname in files:
        src = os.path.join(root, fname)
        rel = os.path.relpath(src, template_dir).replace('\\', '/')
        dst = os.path.join(dest_dir, rel)

        if os.path.exists(dst) and not force:
            print(f"  SKIP  {rel}")
            continue

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        try:
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            content = substitute(content)
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(content)
        except UnicodeDecodeError:
            import shutil
            shutil.copy2(src, dst)

        action = "OVERWRITE" if os.path.exists(dst) and force else "COPY"
        print(f"  {action}  {rel}")
PYEOF

# settings.json (skip if exists)
SETTINGS="$DEST_DIR/settings.json"
if [[ ! -f "$SETTINGS" ]]; then
    LANG_VAL=$("$PYTHON" -c "import json; p=json.load(open('$(to_win "$PRESET_FILE")')); print(p['$PRESET']['LANG'])" 2>/dev/null || echo "$PRESET")
    mkdir -p "$DEST_DIR"
    cat > "$SETTINGS" << EOF
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: This project uses ${LANG_VAL}. Do not mix syntax versions.'"
          }
        ]
      }
    ]
  }
}
EOF
    echo "  CREATE settings.json"
fi

# .gitignore
GITIGNORE="$(pwd)/.gitignore"
touch "$GITIGNORE"
for entry in ".claude/" ".codex_tmp/"; do
    if ! grep -qF "$entry" "$GITIGNORE"; then
        echo "$entry" >> "$GITIGNORE"
        echo "  GITIGNORE += $entry"
    fi
done

echo ""
echo "=== Done ==="
echo ""
echo "Next:"
echo "  /research                → コードベース分析"
echo "  /plan <機能>             → 設計（Discussion Points を含む）"
echo "  /sonnet-dp-research      → Discussion Points を外部調査（省略可）"
echo "  /codex-plan-review       → Codex と設計議論"
echo "  /implement               → 実装"
