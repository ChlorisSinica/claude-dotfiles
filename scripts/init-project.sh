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
    content = content.replace('{{LANG}}',               p.get('LANG', ''))
    content = content.replace('{{VERIFY_CMD}}',         p.get('VERIFY_CMD', ''))
    content = content.replace('{{LANG_RULES}}',         p.get('LANG_RULES', ''))
    content = content.replace('{{SYNTAX_CHECK_CMD}}',   p.get('SYNTAX_CHECK_CMD', ''))
    content = content.replace('{{FILE_PATTERNS}}',      p.get('FILE_PATTERNS', ''))
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

# Generate settings.json, CLAUDE.md, settings.local.json, and syntax-check hook via Python
"$PYTHON" - "$PRESET" "$DEST_DIR_PY" "$PRESET_FILE_PY" "$FORCE" <<'PYEOF2'
import sys, json, os

preset_name, dest_dir, preset_file, force_str = sys.argv[1:5]
force = force_str == "true"

with open(preset_file, encoding='utf-8') as f:
    presets = json.load(f)
p = presets[preset_name]

lang = p.get('LANG', preset_name)
verify_cmd = p.get('VERIFY_CMD', '')
lang_rules = p.get('LANG_RULES', '')
syntax_cmd = p.get('SYNTAX_CHECK_CMD', '')
syntax_enabled = p.get('SYNTAX_CHECK_ENABLED', False)
file_patterns = p.get('FILE_PATTERNS', '')

# Derive file extensions from FILE_PATTERNS (e.g. "**/*.py" -> [".py"])
exts = []
for pat in file_patterns.split(','):
    pat = pat.strip()
    if '*.' in pat:
        exts.append('.' + pat.split('*.')[-1])

def write_if_new(path, content, label):
    if os.path.exists(path) and not force:
        print(f"  SKIP  {label}")
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f"  CREATE {label}")
    return True

# --- settings.json ---
settings_path = os.path.join(dest_dir, 'settings.json')
settings_obj = None

if os.path.exists(settings_path):
    # Backfill: add PostToolUse to existing settings.json if missing
    with open(settings_path, encoding='utf-8') as f:
        settings_obj = json.load(f)
    hooks = settings_obj.setdefault('hooks', {})
    if syntax_enabled and syntax_cmd and 'PostToolUse' not in hooks:
        hooks['PostToolUse'] = [
            {
                "matcher": "Edit|Write",
                "hooks": [{
                    "type": "command",
                    "command": "python .claude/hooks/syntax-check.py",
                    "timeout": 15,
                    "statusMessage": "Syntax check..."
                }]
            }
        ]
        with open(settings_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(settings_obj, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print("  UPDATE settings.json (added PostToolUse)")
    else:
        print("  SKIP  settings.json")
else:
    # New settings.json
    settings_obj = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "compact",
                    "hooks": [{
                        "type": "command",
                        "command": f"echo 'Reminder: This project uses {lang}. Do not mix syntax versions.'"
                    }]
                }
            ]
        }
    }
    if syntax_enabled and syntax_cmd:
        settings_obj["hooks"]["PostToolUse"] = [
            {
                "matcher": "Edit|Write",
                "hooks": [{
                    "type": "command",
                    "command": "python .claude/hooks/syntax-check.py",
                    "timeout": 15,
                    "statusMessage": "Syntax check..."
                }]
            }
        ]
    write_if_new(settings_path, json.dumps(settings_obj, indent=2, ensure_ascii=False) + '\n', 'settings.json')

# --- hooks/syntax-check.py ---
if syntax_enabled and syntax_cmd:
    hook_path = os.path.join(dest_dir, 'hooks', 'syntax-check.py')
    ext_list = repr(exts)
    hook_content = f'''#!/usr/bin/env python3
"""PostToolUse hook: syntax check for {lang} files."""
import json, sys, os, subprocess

EXTENSIONS = {ext_list}
SYNTAX_CMD = {repr(syntax_cmd)}

def main():
    data = json.load(sys.stdin)
    file_path = data.get("tool_input", {{}}).get("file_path", "")
    if not file_path:
        return
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in EXTENSIONS:
        return
    cmd = SYNTAX_CMD.replace("$FILE", file_path)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        print(output, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    write_if_new(hook_path, hook_content, 'hooks/syntax-check.py')

# --- CLAUDE.md ---
claude_md_path = os.path.join(dest_dir, 'CLAUDE.md')
claude_md = f"""# {lang} Project

## Language

{lang}。構文バージョンを混同しないこと。

## Coding Rules

{lang_rules}

## Testing

検証コマンド: `{verify_cmd}`
"""
write_if_new(claude_md_path, claude_md, 'CLAUDE.md')

# --- settings.local.json ---
local_path = os.path.join(dest_dir, 'settings.local.json')
local_obj = {
    "permissions": {
        "allow": [
            "Bash(git *)",
            "Bash(codex review:*)",
            "Bash(powershell *)"
        ]
    }
}
write_if_new(local_path, json.dumps(local_obj, indent=2, ensure_ascii=False) + '\n', 'settings.local.json')
PYEOF2

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
