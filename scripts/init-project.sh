#!/usr/bin/env bash
# init-project.sh
# Usage: bash ~/.claude/scripts/init-project.sh [-t <template>] <preset> [-f] [--workflow-only]
#
# Copies .claude/ templates into the current directory and substitutes
# placeholders from presets.json.
# Existing files are NOT overwritten unless -f is specified.
# Use --workflow-only to update managed workflow files while preserving
# project context and runtime state.

set -euo pipefail

PRESET=""
FORCE=false
TEMPLATE="project-init"
WORKFLOW_ONLY=false

for arg in "$@"; do
    case "$arg" in
        -f) FORCE=true ;;
        --workflow-only|--skills-only) WORKFLOW_ONLY=true ;;
        -t) :;;  # value consumed below
        *)
            # If previous arg was -t, this is the template name
            if [[ "${PREV_ARG:-}" == "-t" ]]; then
                TEMPLATE="$arg"
            else
                PRESET="$arg"
            fi
            ;;
    esac
    PREV_ARG="$arg"
done

if [[ -z "$PRESET" ]]; then
    echo "ERROR: preset name required" >&2
    echo "Usage: bash ~/.claude/scripts/init-project.sh [-t <template>] <preset> [-f] [--workflow-only]" >&2
    echo "" >&2
    echo "Templates: project-init (default), research-survey" >&2
    echo "Presets (project-init): python, python-pytorch, typescript, rust, ahk, ahk-v2, cpp-msvc" >&2
    echo "Presets (research-survey): survey-cv, survey-ms" >&2
    exit 1
fi

TEMPLATE_DIR="${HOME}/.claude/templates/${TEMPLATE}/.claude"
PRESET_FILE="${HOME}/.claude/templates/${TEMPLATE}/presets.json"
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
"$PYTHON" - "$PRESET" "$TEMPLATE_DIR_PY" "$DEST_DIR_PY" "$PRESET_FILE_PY" "$FORCE" "$WORKFLOW_ONLY" <<'PYEOF'
import sys, json, os

preset_name, template_dir, dest_dir, preset_file, force_str, workflow_only_str = sys.argv[1:7]
force = force_str == "true"
workflow_only = workflow_only_str == "true"

with open(preset_file, encoding='utf-8') as f:
    presets = json.load(f)

if preset_name not in presets:
    print(f"ERROR: Unknown preset '{preset_name}'", file=sys.stderr)
    print(f"Available: {', '.join(presets.keys())}", file=sys.stderr)
    sys.exit(1)

p = presets[preset_name]

def substitute(content):
    for key, value in p.items():
        content = content.replace('{{' + key + '}}', str(value))
    return content

for root, dirs, files in os.walk(template_dir):
    for fname in files:
        src = os.path.join(root, fname)
        rel = os.path.relpath(src, template_dir).replace('\\', '/')
        dst = os.path.join(dest_dir, rel)
        existed_before = os.path.exists(dst)

        if workflow_only:
            is_context_file = rel.startswith('context/')
            is_runtime_state = rel == 'agents/sessions.json'
            if is_context_file or is_runtime_state:
                print(f"  SKIP  {rel} (workflow-only)")
                continue

        if existed_before and not force:
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

        action = "OVERWRITE" if existed_before else "COPY"
        print(f"  {action}  {rel}")
PYEOF

# Generate settings.json, CLAUDE.md, settings.local.json, and syntax-check hook via Python
"$PYTHON" - "$PRESET" "$DEST_DIR_PY" "$PRESET_FILE_PY" "$FORCE" "$TEMPLATE" <<'PYEOF2'
import sys, json, os

preset_name, dest_dir, preset_file, force_str, template = sys.argv[1:6]
force = force_str == "true"

with open(preset_file, encoding='utf-8') as f:
    presets = json.load(f)
p = presets[preset_name]

is_research = template == "research-survey"

def write_if_new(path, content, label):
    existed_before = os.path.exists(path)
    if existed_before and not force:
        print(f"  SKIP  {label}")
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    action = "OVERWRITE" if existed_before else "CREATE"
    print(f"  {action}  {label}")
    return True

# --- settings.json ---
settings_path = os.path.join(dest_dir, 'settings.json')

if is_research:
    # Research template: simple SessionStart reminder
    domain = p.get('DOMAIN', preset_name)
    if not os.path.exists(settings_path) or force:
        settings_obj = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "compact",
                        "hooks": [{
                            "type": "command",
                            "command": f"echo 'Reminder: This is a research survey project. Domain: {domain}. Use /scope to begin.'"
                        }]
                    }
                ]
            }
        }
        write_if_new(settings_path, json.dumps(settings_obj, indent=2, ensure_ascii=False) + '\n', 'settings.json')
    else:
        print("  SKIP  settings.json")
else:
    # Development template: SessionStart + optional PostToolUse syntax check
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

    if force:
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
    elif os.path.exists(settings_path):
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

    # --- hooks/syntax-check.py (dev template only) ---
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

    # --- CLAUDE.md (dev template) ---
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

# --- CLAUDE.md (research template) ---
if is_research:
    domain = p.get('DOMAIN', preset_name)
    survey_rules = p.get('SURVEY_RULES', '')
    key_venues = p.get('KEY_VENUES', '')
    claude_md_path = os.path.join(dest_dir, 'CLAUDE.md')
    claude_md = f"""# Research Survey — {domain}

## Domain

{domain}

## Key Venues

{key_venues}

## Survey Methodology Rules

{survey_rules}

## Tools

推奨 CLI ツール（全てオプション）:
- `pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure`
- Pandoc: `winget install --id JohnMacFarlane.Pandoc`

ツール検出: `/check-tools`

## Workflow

`/scope` → `/search` → `/read` → `/outline` → `/draft` → `/review` → `/convert`
"""
    write_if_new(claude_md_path, claude_md, 'CLAUDE.md')

# --- settings.local.json (both templates, different permissions) ---
local_path = os.path.join(dest_dir, 'settings.local.json')
if is_research:
    local_obj = {
        "permissions": {
            "allow": [
                "Bash(git *)",
                "Bash(pqa *)",
                "Bash(paper *)",
                "Bash(marker_single *)",
                "Bash(bibcure *)",
                "Bash(pandoc *)",
                "Bash(python -c *)",
                "Bash(python3 -c *)",
                "Bash(powershell *)"
            ]
        }
    }
else:
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
if [[ "$TEMPLATE" == "research-survey" ]]; then
    echo "  /scope <topic>           → 研究スコープ定義"
    echo "  /search                  → 文献検索"
    echo "  /read                    → 論文分析"
    echo "  /outline                 → サーベイ構成案"
    echo "  /draft                   → 執筆"
    echo "  /review                  → 品質レビュー"
    echo "  /convert                 → Markdown → LaTeX 変換"
else
    echo "  /research                → コードベース分析"
    echo "  /plan <機能>             → 設計（Discussion Points を含む）"
    echo "  /sonnet-dp-research      → Discussion Points を外部調査（省略可）"
    echo "  /codex-plan-review       → Codex と設計議論"
    echo "  /implement               → 実装"
fi
