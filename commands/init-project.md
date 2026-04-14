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
   ```powershell
   ~/.claude/scripts/init-project.ps1 -t <template> <preset>
   ```
   Codex 主体テンプレートの場合:
   ```powershell
   ~/.claude/scripts/init-project.ps1 --codex-main <preset>
   ```
   ※ `--codex-main` の正規入口は上記 `.ps1` 直呼びとし、`/init-project --codex-main ...` は Claude Code からの互換入口として扱う
   強制上書きする場合:
   ```powershell
   ~/.claude/scripts/init-project.ps1 -t <template> <preset> -f
   ```
   workflow-managed files を更新しつつ `.claude/context` と runtime state を維持したい場合:
   ```powershell
   ~/.claude/scripts/init-project.ps1 -t <template> <preset> --workflow-only -f
   ```
   `~/.claude/...` を使うこと。`/.claude/...` は Windows では `C:\.claude\...` になるので使わない。

3. **完了報告**:
   スクリプトの出力をそのまま表示し、次のステップを案内する。

## 注意

- スクリプトが `Template not found` で失敗した場合は `bash ~/claude-dotfiles/setup.sh` を実行するよう案内
- 不明なプリセット名はスクリプトがエラーを出力するので、そのまま報告する
- 新しく展開された repo-local commands / skills は、Claude Code / Codex の起動中セッションには即時反映されないことがある。必要なら一度セッションを開き直すか再起動するよう案内する
- `--codex-main` は `.agents/skills/` と `.agents/context/` を主軸としたテンプレートを生成し、review runner `scripts/run-codex-*-review.ps1` と Codex ランタイム設定 `.claude/settings.json` / `.claude/settings.local.json(.bak)` を出力する
- `--workflow-only -f` は `.claude/context/` と `.claude/agents/sessions.json` を保持しつつ、template-managed files と generated workflow files（`.claude/CLAUDE.md`、`.claude/settings.json`、`.claude/settings.local.json`、`.claude/hooks/syntax-check.py`、`.gitignore` を含む）を更新する
- `--skills-only` は後方互換 alias として残るが、今後は `--workflow-only` を優先する
- 既存プロジェクトで workflow files だけ更新したい場合は `/update-workflow` を案内してよい
