---
description: "既存プロジェクトの workflow files を更新し、テンプレートに応じた context を保持"
---

# Update Workflow — 既存プロジェクトの workflow files 更新

既存プロジェクトの workflow-managed files を更新してください。
テンプレートに応じた context と runtime state は保持します。

## 入力

- `$ARGUMENTS`: プリセット名（省略可）
  - 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`
  - 研究用: `survey-cv`, `survey-ms`
- 必要に応じて `--codex-main` を付けて Codex 主体テンプレートを更新可能

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
     - `.bib` ファイルや `papers/` ディレクトリがある場合 → `research-survey` テンプレートを提案
   - 判断できない場合はユーザーに選択肢を提示して確認

2. **workflow-only 更新を実行**:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py -t <template> <preset> --workflow-only -f
   ```
   Codex 主体テンプレートの場合:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py --codex-main <preset> --workflow-only -f
   ```
   `--codex-main` では `<python-launcher>` に `python`, `python3`, `py -3` など、その環境で使える Python 3.11+ launcher を入れる
   `~/.claude/...` を使うこと。`/.claude/...` は Windows では `C:\.claude\...` になるので使わない。

3. **完了報告**:
   スクリプトの出力をそのまま表示し、テンプレートに応じたローカル作業資産を保持したまま workflow files を更新したことを伝える。

## 注意

- Codex 主体テンプレートで `Template not found` や Python runner 不足で失敗した場合は `<python-launcher> ~/claude-dotfiles/scripts/setup.py --codex -f` を案内する
- non-`--codex-main` テンプレートで `Template not found` になった場合も `<python-launcher> ~/claude-dotfiles/scripts/setup.py -f` を案内する
- 不明なプリセット名はスクリプトがエラーを出力するので、そのまま報告する
- `--workflow-only -f` は `.claude/context/` と `.claude/agents/sessions.json` を保持しつつ、template-managed files と generated workflow files（`.claude/CLAUDE.md`、`.claude/settings.json`、`.claude/settings.local.json`、`.claude/hooks/syntax-check.py`、`.gitignore` を含む）を更新する
- `--codex-main --workflow-only -f` は `.agents/context/` と `.agents/reviews/` を保持しつつ、`.agents/skills/`、prompt/template 資産、`.claude/settings.json`、`.claude/settings.local.json(.bak)`、`scripts/run-verify.py`、`scripts/run-codex-*.py`、`.gitignore` を更新する
