---
description: "プロジェクトに Claude Code × Codex 連携環境をセットアップ"
---

# Init Project — Claude Code × Codex 連携環境のセットアップ

## 入力

- `$ARGUMENTS`: プリセット名（省略可）
  - 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`
  - 研究用: `survey-cv`, `survey-ms`
- 必要に応じて `--codex-main` を付けて Codex 主体テンプレートを選択可能

## 手順

1. **テンプレートとプリセットの選択**:
   - `--codex-main` が指定された場合: テンプレート = `codex-main`
   - `$ARGUMENTS` が `survey-` で始まる場合: テンプレート = `research-survey`
   - それ以外: テンプレート = `project-init`（デフォルト）
   - `$ARGUMENTS` が指定されていればそのプリセットを使用
   - 空の場合: プロジェクト内のファイルを調べて自動検出
     - `.py` → `python`（requirements.txt / pyproject.toml に `torch` があれば `python-pytorch`）
     - `.ts` / `.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → ユーザーに v1 / v2 を確認
     - `.sln` または `.vcxproj` → `cpp-msvc`
     - `.unity` または `Assets/` + `ProjectSettings/` ディレクトリ → `unity`
     - `.blend` → `blender`
     - `.bib` ファイルや `papers/` ディレクトリがある場合 → 研究テンプレートを提案
   - 判断できない場合はユーザーに選択肢を提示して確認

2. **スクリプト実行**:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t <template> <preset>
   ```
   ここでも `<python-launcher>` には `python`, `python3`, `py -3` など、その環境で使える Python 3.11+ launcher を入れる
   Codex 主体テンプレートの場合:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py --codex-main <preset>
   ```
   ※ `--codex-main` の正規入口は上記 Python runner 直呼びとし、`/init-project --codex-main ...` は Claude Code からの互換入口として扱う。`<python-launcher>` には `python`, `python3`, `py -3` など、その環境で使える Python 3.11+ launcher を入れる
   強制上書きする場合:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t <template> <preset> -f
   ```
   workflow-managed files を更新しつつ `.claude/context` と runtime state を維持したい場合:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t <template> <preset> --workflow-only -f
   ```
   Codex 主体テンプレートの workflow refresh は:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py --codex-main <preset> --workflow-only -f
   ```
   `~/.claude/...` を使うこと。`/.claude/...` は Windows では `C:\.claude\...` になるので使わない。

3. **完了報告**:
   スクリプトの出力をそのまま表示し、次のステップを案内する。

## 注意

- Codex 主体テンプレートで `Template not found` や Python runner 不足で失敗した場合は `<python-launcher> ~/claude-dotfiles/scripts/setup.py --codex` を案内する
- non-`--codex-main` テンプレートで `Template not found` になった場合も `<python-launcher> ~/claude-dotfiles/scripts/setup.py -f` を案内する
- 不明なプリセット名はスクリプトがエラーを出力するので、そのまま報告する
- 新しく展開された repo-local commands / skills は、Claude Code / Codex の起動中セッションには即時反映されないことがある。必要なら一度セッションを開き直すか再起動するよう案内する
- `--codex-main` は `.agents/skills/` と `.agents/context/` を主軸としたテンプレートを生成し、Python review runner `scripts/run-codex-*.py`、`scripts/run-verify.py`、Codex ランタイム設定 `.claude/settings.json` / `.claude/settings.local.json(.bak)` を出力する
- `--workflow-only -f` は `.claude/context/` と `.claude/agents/sessions.json` を保持しつつ、template-managed files と generated workflow files（`.claude/CLAUDE.md`、`.claude/settings.json`、`.claude/settings.local.json`、`.claude/hooks/syntax-check.py`、`.gitignore` を含む）を更新する
- `--skills-only` は後方互換 alias として残るが、今後は `--workflow-only` を優先する
- 既存プロジェクトで workflow files だけ更新したい場合は `/update-workflow` を案内してよい
