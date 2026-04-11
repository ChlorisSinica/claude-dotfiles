---
description: "プロジェクトに Claude Code × Codex 連携環境をセットアップ"
---

# Init Project — Claude Code × Codex 連携環境のセットアップ

## 入力

- `$ARGUMENTS`: プリセット名（省略可）
  - 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`
  - 研究用: `survey-cv`, `survey-ms`

## 手順

1. **テンプレートとプリセットの選択**:
   - `$ARGUMENTS` が `survey-` で始まる場合: テンプレート = `research-survey`
   - それ以外: テンプレート = `project-init`（デフォルト）
   - `$ARGUMENTS` が指定されていればそのプリセットを使用
   - 空の場合: プロジェクト内のファイルを調べて自動検出
     - `.py` → `python`（requirements.txt / pyproject.toml に `torch` があれば `python-pytorch`）
     - `.ts` / `.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → ユーザーに v1 / v2 を確認
     - `.sln` または `.vcxproj` → `cpp-msvc`
     - `.bib` ファイルや `papers/` ディレクトリがある場合 → 研究テンプレートを提案
   - 判断できない場合はユーザーに選択肢を提示して確認

2. **スクリプト実行**:
   ```bash
   bash ~/.claude/scripts/init-project.sh -t <template> <preset>
   ```
   強制上書きする場合:
   ```bash
   bash ~/.claude/scripts/init-project.sh -t <template> <preset> -f
   ```
   commands / agents だけ更新して `.claude/context` や project-specific settings を維持したい場合:
   ```bash
   bash ~/.claude/scripts/init-project.sh -t <template> <preset> --workflow-only -f
   ```

3. **完了報告**:
   スクリプトの出力をそのまま表示し、次のステップを案内する。

## 注意

- スクリプトが `Template not found` で失敗した場合は `bash ~/claude-dotfiles/setup.sh` を実行するよう案内
- 不明なプリセット名はスクリプトがエラーを出力するので、そのまま報告する
- `--workflow-only -f` は `.claude/commands/` と `.claude/agents/` を更新するが、`.claude/context/`、`CLAUDE.md`、`settings.json`、`settings.local.json`、`.gitignore`、`agents/sessions.json` は保持する
- `--skills-only` は後方互換 alias として残るが、今後は `--workflow-only` を優先する
- 既存プロジェクトで workflow files だけ更新したい場合は `/update-workflow` を案内してよい
