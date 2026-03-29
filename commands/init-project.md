---
description: "プロジェクトに Claude Code × Codex 連携環境をセットアップ"
---

# Init Project — Claude Code × Codex 連携環境のセットアップ

現在のプロジェクトに `.claude/agents/`, `.claude/context/`, `.claude/commands/` の連携環境をセットアップしてください。

## 入力

- `$ARGUMENTS`: 言語プリセット名（省略可）
  - 例: `python`, `python-pytorch`, `typescript`, `rust`, `autohotkey-v1`, `autohotkey-v2`
  - 空の場合: プロジェクトのファイル構成から自動検出、または選択肢を提示

## 手順

1. **プリセット選択**:
   - `$ARGUMENTS` が指定されていればそのプリセットを使用
   - 空の場合: プロジェクト内のファイル拡張子を調べて自動検出を試みる
     - `.py` → `python` (requirements.txt に `torch` があれば `python-pytorch`)
     - `.ts`/`.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → ユーザーに v1 / v2 を確認
   - 自動検出できない場合: ユーザーに選択肢を提示

2. **テンプレートのコピー**:
   - `~/.claude/templates/project-init/` から以下をコピー:
     - `.claude/agents/` フォルダ全体 (prompts/, workflows/, COMMANDS_GUIDE.md, master_workflow.md, sessions.json)
     - `.claude/commands/` フォルダ全体 (9つのスラッシュコマンド: research, plan, implement, codex-research-review, codex-plan-review, codex-impl-review, codex-review, handover, retro)
     - `.claude/context/` フォルダ（空、.gitkeep のみ）
   - **既存ファイルは上書きしない**（スキップしてユーザーに通知）

3. **プレースホルダー置換**:
   - `~/.claude/templates/project-init/presets.json` からプリセット設定を読み込む
   - 以下のファイル内のプレースホルダーを置換:
     - `.claude/agents/master_workflow.md`: `{{LANG}}`, `{{VERIFY_CMD}}`
     - `.claude/agents/prompts/codex_impl_review.md`: `{{LANG}}`, `{{LANG_RULES}}`
     - `.claude/commands/research.md`: `{{LANG}}`, `{{VERIFY_CMD}}`
     - `.claude/commands/plan.md`: `{{LANG}}`, `{{VERIFY_CMD}}`
     - `.claude/commands/implement.md`: `{{VERIFY_CMD}}`
   - **注意**: Windows パスのバックスラッシュは置換時に消えやすい。`sed` ではなく、ファイルを Read → Edit で置換すること。

4. **settings.json の確認** (存在しない場合のみ作成):
   ```json
   {
     "hooks": {
       "SessionStart": [
         {
           "matcher": "compact",
           "hooks": [
             {
               "type": "command",
               "command": "echo 'Reminder: This project uses {{LANG}}. Do not mix syntax versions.'"
             }
           ]
         }
       ]
     }
   }
   ```
   ※ 既存の `.claude/settings.json` がある場合はスキップ

5. **.gitignore の更新**:
   - 以下のエントリがなければ追加:
     ```
     .claude/
     .codex_tmp/
     ```
   - `.claude/` を gitignore することで agents/, context/, commands/ 全てが除外される
   - プロジェクトルートの `CLAUDE.md` は Git 管理したい場合はルートに配置、不要なら `.claude/CLAUDE.md` に配置

6. **完了報告**:
   - セットアップしたファイル一覧を表示
   - 次のステップを案内:
     ```
     セットアップ完了！以下の流れで開始できます:
     1. /research で research.md を作成（データフロー・依存関係を含む全ファイル分析）
     2. /codex-research-review で Codex レビュー
     3. /plan <機能の説明> で plan.md + tasks.md を作成
     4. /codex-plan-review で Codex と設計議論
     5. /implement で実装 → /codex-impl-review で Codex レビュー
     ```

## 注意

- テンプレートが `~/.claude/templates/project-init/` に存在しない場合はエラーを表示
- 既存の `.claude/agents/` や `.claude/commands/` があるプロジェクトでは差分のみ追加
- プリセットにない言語の場合はプレースホルダーをそのまま残し、手動設定を案内
- AGENTS.md はルートに作成しない（Codex は Claude 経由で呼び出すため不要）
