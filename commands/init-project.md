---
description: "プロジェクトに Claude Code × Codex 連携環境をセットアップ"
---

# Init Project — Claude Code × Codex 連携環境のセットアップ

現在のプロジェクトに `.agents/`, `.context/`, `.claude/commands/` の連携環境をセットアップしてください。

## 入力

- `$ARGUMENTS`: 言語プリセット名（省略可）
  - 例: `python`, `python-pytorch`, `typescript`, `rust`, `autohotkey-v2`
  - 空の場合: プロジェクトのファイル構成から自動検出、または選択肢を提示

## 手順

1. **プリセット選択**:
   - `$ARGUMENTS` が指定されていればそのプリセットを使用
   - 空の場合: プロジェクト内のファイル拡張子を調べて自動検出を試みる
     - `.py` → `python` (requirements.txt に `torch` があれば `python-pytorch`)
     - `.ts`/`.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → `autohotkey-v2`
   - 自動検出できない場合: ユーザーに選択肢を提示

2. **テンプレートのコピー**:
   - `~/.claude/templates/project-init/` から以下をコピー:
     - `.agents/` フォルダ全体 (prompts/, workflows/, COMMANDS_GUIDE.md, master_workflow.md, sessions.json)
     - `.claude/commands/` フォルダ全体 (9つのスラッシュコマンド: research, plan, implement, codex-research-review, codex-plan-review, codex-impl-review, codex-review, handover, retro)
     - `.context/` フォルダ（空、.gitkeep のみ）
   - **既存ファイルは上書きしない**（スキップしてユーザーに通知）

3. **プレースホルダー置換**:
   - `~/.claude/templates/project-init/presets.json` からプリセット設定を読み込む
   - 以下のファイル内のプレースホルダーを置換:
     - `.agents/master_workflow.md`: `{{LANG}}`, `{{VERIFY_CMD}}`
     - `.agents/prompts/codex_impl_review.md`: `{{LANG}}`, `{{LANG_RULES}}`
     - `.claude/commands/research.md`: `{{LANG}}`, `{{VERIFY_CMD}}`
     - `.claude/commands/plan.md`: `{{LANG}}`, `{{VERIFY_CMD}}`
     - `.claude/commands/implement.md`: `{{VERIFY_CMD}}`

4. **settings.json の作成** (存在しない場合):
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "bash .claude/statusline-command.sh"
     }
   }
   ```
   ※ 既存の `.claude/settings.json` がある場合はスキップ

5. **.gitignore の更新**:
   - 以下のエントリがなければ追加:
     ```
     # Claude Code × Codex
     .context/research.md
     .context/codex_plan_tasks_review.md
     .agents/sessions.json
     ```

6. **完了報告**:
   - セットアップしたファイル一覧を表示
   - 次のステップを案内:
     ```
     セットアップ完了！以下の流れで開始できます:
     1. /research で research.md を作成（データフロー・依存関係を含む全ファイル分析）
     2. /codex-research-review で Codex レビュー
     3. /plan <機能の説明> で plan.md + tasks.md を作成
     4. /codex-plan-review で Codex クロスレビュー
     5. /implement で実装 → /codex-impl-review で Codex 厳格レビュー
     ```

## 注意

- テンプレートが `~/.claude/templates/project-init/` に存在しない場合はエラーを表示
- 既存の `.agents/` や `.claude/commands/` があるプロジェクトでは差分のみ追加
- プリセットにない言語の場合はプレースホルダーをそのまま残し、手動設定を案内
