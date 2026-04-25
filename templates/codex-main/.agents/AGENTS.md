# {{LANG}} プロジェクト

## 目的

このファイルは、このリポジトリで Codex-first に作業するときのローカル運用契約です。
`.agents/` 配下の資産とあわせて使用してください。

## 言語

- 主なスタック: {{LANG}}
- 検証コマンド: `{{VERIFY_CMD}}`

## ワークフロー

1. コードベースを調査し、結果を `.agents/context/research.md` に記録する
2. 実装方針を `.agents/context/plan.md` にまとめる
3. 検証可能なタスクへ分解して `.agents/context/tasks.md` に書く
4. `codex-plan-review` で plan/tasks をレビューしてから実装に進む
5. 変更は小さく安全に実装する
6. 意味のある変更ごとに検証を実行する
7. 実装がまとまったら `codex-impl-review` で収束するまで review / 修正を回す
8. 長い review や recovery / alignment が続いたら、必要に応じて `handover-skills` で再開手順を残す
9. review 結果を `.agents/reviews/` に保存する
10. プロジェクト全体検証は `{{PYTHON_LAUNCHER}} .claude/scripts/run-verify.py` を優先する

## 作業ルール

- 実際のファイル内容を読んでから設計や挙動を論じる
- 観測した事実と推測を分ける
- 変更は局所的に行い、無関係なリファクタは避ける
- 明確な理由がない限り、既存の実装パターンを優先する
- 外部製品、価格、バージョン、ベンダー挙動に依存する判断は時変情報として扱い、都度確認する

## 責務分担

- `setup / init / update` のような決定的処理は Python runner に寄せる
- `research / plan / implement` の判断と進行は `skills` と `prompts` を主役にする
- review は二層に分ける
- `skills / prompts` は review の観点、停止条件、次に何をするかを定義する
- `.agents/scripts/run-codex-*.py` は 1 実行 = 1 cycle の bundle 作成、`codex review -` 実行、結果保存など機械的処理だけを担う
- review runner の実行は `{{PYTHON_LAUNCHER}} .agents/scripts/...py` を正規経路にする
- review runner に運用ルールを重複実装しすぎない

## コミットメッセージ

- 1行目 (subject): 英語。imperative form (e.g. `Fix authentication bug`)
- 2行目: 空行
- 3行目以降 (body): 日本語の箇条書きを基本とする。変更理由・詳細を箇条書きで記述

## コーディングルール

{{LANG_RULES}}

## 調査スコープ

- 優先して読むソース: `{{FILE_PATTERNS}}`
- 通常は読まない generated / vendor / cache 系ディレクトリやパス: `{{EXCLUDE_DIRS}}`
- 通常は読まない generated / vendor メタデータ系ファイルパターン: `{{EXCLUDE_FILE_PATTERNS}}`
- `.` 始まりと `_` 始まりのディレクトリも、タスクが明示的に対象にしない限り調査対象外

## ローカル資産

- `.agents/context/` : 調査、計画、タスク、snippet、failure report
- `.agents/context/_codex_input.tmp` : `codex review -` に渡す一時入力
- `.agents/context/codex_plan_arch_review.md` : plan review Phase A の中間結果
- `.agents/context/codex_plan_tasks_review.md` : plan review Phase B の中間結果
- `.agents/context/codex_impl_review.md` : impl review の中間結果
- `.agents/context/implementation_gap_audit.md` : plan / implementation mismatch の監査メモ
- `.agents/context/skill_handover_issues.md` : skill 運用上の詰まりどころ
- `.agents/context/handover_skills_procedure.md` : 次担当者向けの再開手順
- `.agents/skills/` : repo-local の Codex workflow skills
- `.agents/skills/handover-skills/` : 長い cycle の handover 整理
- `.agents/prompts/` : fallback prompt と手動 bridge 用 prompt
- `.agents/reviews/` : 保存済みレビュー結果
- `.agents/reviews/sessions.json` : review cycle の観測値と APPROVED 記録
  - `plan-arch-review.md`
  - `plan-review.md`
  - `impl-review.md`
- `.agents/templates/` : 再利用用テンプレート
- `.agents/scripts/run-codex-plan-review.py` : plan review runner
- `.agents/scripts/run-codex-impl-review.py` : impl review runner
- `.claude/scripts/run-verify.py` : verify runner

## Sonnet Bridge

外部調査が必要な Discussion Point を Claude / Sonnet に手動委譲するときは、次を使用します。

- `.agents/skills/sonnet-dp-research-bridge/`
- `.agents/prompts/sonnet-dp-research.md`
- `.agents/templates/sonnet-dp-research-input.md`

このテンプレートでは `.claude/` が存在する前提を置かないこと。
