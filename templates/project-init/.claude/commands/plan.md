---
description: "Phase 2: plan.md + tasks.md の作成"
---

# plan.md, tasks.md の作成

## 入力

- `$ARGUMENTS`: 機能の説明（必須）
  - 例: `/plan SettingWindowのGUI設定値を本番学習エンジンに接続する`

## プロジェクト情報

- **言語/フレームワーク**: {{LANG}}
- **検証コマンド**: `{{VERIFY_CMD}}`

## 前提

- `.claude/context/research.md` が存在すること（存在しない場合はユーザーに通知）
- research.md の**データフローセクション**を必ず参照し、既存の変数/コールバック/ファイル形式との整合性を確認すること

## 仕様確認ステップ（条件付き）

plan 作成の前に、`$ARGUMENTS` と `research.md` を分析し、**仕様として確定しきれない曖昧な点**がある場合のみユーザーに質問する。

- 質問は AskUserQuestion ツールを使用
- 質問対象: 技術的な仕様の曖昧さ、スコープの境界、既存実装との整合性で判断が分かれる点
- 質問対象外: 優先度、スケジュール、実装順序（これらは Claude が判断する）
- 質問数: 最大3問。まとめて1回で質問する（何度もやりとりしない）
- 曖昧な点がなければ質問せずそのまま plan 作成に進む

## プロンプト

**Feature**: $ARGUMENTS

plan.md, tasks.md must include:

1. Objective (with verifiable success criteria / Definition of Done)
2. Non-objectives (what is explicitly NOT in scope)
3. Approach (technical strategy, alternatives with trade-offs)
4. File-level change list (full paths, what changes in each)
5. Implementation details (code snippets based on actual codebase)
6. **Data flow impact analysis** — 変更によって影響を受けるデータフロー（コールバック、設定値、ファイル I/O）の全経路を明示
7. **Script dependency changes** — 追加/削除/変更される import、関数呼び出し、変数の受け渡しの一覧
8. Risk + rollback plan
9. Verification commands per task
10. TODO list (phased, checkbox format, each task has its own DoD)

Rules:
- Code snippets must be based on actual codebase (don't guess).
- research.md のデータフローセクションを参照し、既存インターフェースとの整合性を確認すること.
- 新規パラメータを追加する場合、その値の生成元→伝播経路→消費先を全て明記すること.
- List every affected file with its full path.
- Don't implement yet.
- TODO items must be verifiable granularity.
- **Non-Objectives 安全弁**: ユーザーの入力テキスト (`$ARGUMENTS`) に明示的に含まれる要望を Non-Objectives に分類してはならない。スコープから除外したい場合は、plan 作成前にユーザーに確認すること。Non-Objectives には「ユーザーが言及していない関連機能」のみを記載する。
- **言語制約**: このプロジェクトは {{LANG}} です。検証コマンドは `{{VERIFY_CMD}}` を基準に設計すること。他の言語のツール（例: 別言語のインタプリタ）を検証コマンドに含めないこと。

## 構造ルール

### ファイル分離
- plan.md: 設計判断 + アーキテクチャ + テーブル定義（状態遷移、コールバック契約等）
- tasks.md: タスク分解 + DoD（plan.md の仕様は参照のみ、コピーしない）
- snippets.md: コードスニペット集（擬似コードとして明記）

### Single Source of Truth
- 状態遷移表、コールバック契約表等の仕様テーブルは plan.md に **1箇所のみ** 定義
- tasks.md の DoD は「plan.md §X.Y の期待値と一致すること」と参照形式で記述
- コードスニペットは snippets.md に配置、plan.md では「snippets.md §X 参照」とのみ記述

### snippets.md のルール
- 先頭に「⚠️ 設計意図を示す擬似コード。実装時に正確な構文に整えること」を明記
- Codex レビューでは構文の厳密性は検証対象外

### サイズガイドライン（目安）
- plan.md: ~500行を超えたら snippets.md への分離を検討
- tasks.md: ~300行を超えたらタスクの粒度を見直し
- （プロジェクト規模に応じて柔軟に調整）

## 出力

- `.claude/context/plan.md` — 冒頭に以下のメタデータブロックを必ず含めること:
  ```markdown
  <!-- USER_REQUEST: $ARGUMENTS -->
  ```
  これは codex-plan-review がユーザー要望カバレッジを検証するために使用する。
- `.claude/context/tasks.md`
- `.claude/context/snippets.md`（コードスニペットがある場合）

## 自動コミット & プッシュ

plan.md / tasks.md / snippets.md の作成が完了したら:

1. `git add .claude/context/plan.md .claude/context/tasks.md .claude/context/snippets.md`（存在するファイルのみ）
2. コミットメッセージ: `docs: create plan.md + tasks.md for <Feature の要約>`
3. `git push`
4. コミット・プッシュ完了をユーザーに報告

**Co-Authored-By**: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` をコミットメッセージ末尾に付与。

## 次のステップ

plan.md / tasks.md の作成完了後、ユーザーに以下を案内すること:

> plan.md を確認し、修正が必要な箇所にインラインコメントを追加してください。
> 書式: `[DELETE]`, `[CHANGE: 説明]`, `[ADD: 説明]`, `[QUESTION: 質問]`
> 修正が完了したら、このチャットに戻ってください。

ユーザーの Annotation Cycle（インラインコメントによる修正指示）が完了した後:
- `/codex-plan-review` で Codex クロスレビューを実行
