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
4. 変更は小さく安全に実装する
5. 意味のある変更ごとに検証を実行する
6. plan / 実装レビュー結果を `.agents/reviews/` に保存する

## 作業ルール

- 実際のファイル内容を読んでから設計や挙動を論じる
- 観測した事実と推測を分ける
- 変更は局所的に行い、無関係なリファクタは避ける
- 明確な理由がない限り、既存の実装パターンを優先する
- 外部製品、価格、バージョン、ベンダー挙動に依存する判断は時変情報として扱い、都度確認する

## コミットメッセージ

- 1行目 (subject): 英語。imperative form (e.g. `Fix authentication bug`)
- 2行目: 空行
- 3行目以降 (body): 日本語可。変更理由・詳細を記述

## コーディングルール

{{LANG_RULES}}

## 調査スコープ

- 優先して読むソース: `{{FILE_PATTERNS}}`
- 通常は読まない generated / vendor / cache 系ディレクトリやパス: `{{EXCLUDE_DIRS}}`
- 通常は読まない generated / vendor メタデータ系ファイルパターン: `{{EXCLUDE_FILE_PATTERNS}}`
- `.` 始まりと `_` 始まりのディレクトリも、タスクが明示的に対象にしない限り調査対象外

## ローカル資産

- `.agents/context/` : 調査、計画、タスク、snippet、failure report
- `.agents/skills/` : repo-local の Codex workflow skills
- `.agents/prompts/` : fallback prompt と手動 bridge 用 prompt
- `.agents/reviews/` : 保存済みレビュー結果
- `.agents/templates/` : 再利用用テンプレート

## Sonnet Bridge

外部調査が必要な Discussion Point を Claude / Sonnet に手動委譲するときは、次を使用します。

- `.agents/skills/sonnet-dp-research-bridge/`
- `.agents/prompts/sonnet-dp-research.md`
- `.agents/templates/sonnet-dp-research-input.md`

このテンプレートでは `.claude/` が存在する前提を置かないこと。
