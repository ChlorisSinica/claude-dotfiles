# Codex Plan/Tasks Review Prompt

> 使用法: `codex exec --full-auto` でプロンプト+plan.md+tasks.md を送信

---

プロジェクトと research.md を読み込んだ上で，opus が作成した .context/plan.md と .context/tasks.md を深く詳細に，一切の妥協無くレビューを行ってください。

このplan.mdとtasks.mdの更新後にCodex（あなた）が実装を行うため，実装を行うにあたって情報が不足している，仕様定義不足，DoD不足，有意義な意見や同意する意見，学んだことや発見の中から該当することを一切見逃さず全て詳細にまとめ，.context/codex_plan_tasks_review.md を作成してください．

opus は以下のルールで plan.md と tasks.md を作成しています．

Feature: $FEATURE

plan.md, tasks.md must include:
1. Objective (with verifiable success criteria / Definition of Done)
2. Non-objectives (what is explicitly NOT in scope)
3. Approach (technical strategy, alternatives with trade-offs)
4. File-level change list (full paths, what changes in each)
5. Implementation details (code snippets based on actual codebase)
6. **Data flow impact analysis** — 変更によって影響を受けるデータフロー（コールバック、設定値、ファイル I/O）の全経路
7. **Script dependency changes** — 追加/削除/変更される import、関数呼び出し、変数の受け渡し
8. Risk + rollback plan
9. Verification commands per task
10. TODO list (phased, checkbox format, each task has its own DoD)

Additional review focus:
- **データフロー整合性**: 新規パラメータの生成元→伝播経路→消費先が全て繋がっているか
- **コールバック互換性**: 既存のコールバックシグネチャとの互換性が維持されているか
- **ファイル I/O 互換性**: JSON/CSV のフィールド名・型が既存コードと整合しているか
- **依存関係の変更**: import の追加/削除が他のファイルに波及しないか

Rules:
- Code snippets must be based on actual codebase (don't guess).
- List every affected file with its full path.
- Don't implement yet.
- TODO items must be verifiable granularity:
  BAD: "implement main feature"
  GOOD: "Add calculateScore() to src/utils/score.ts returning number"
- snippets.md のコードは設計意図を示す擬似コードとして扱い、構文の厳密性は検証対象外とすること

## 判定基準

レビュー結果の末尾に以下の判定を必ず出力すること:

### 判定: APPROVED | CONDITIONAL | REVISE

- **APPROVED**: P0 が 0 件。実装着手可能。
- **CONDITIONAL**: P0 が 0 件だが P1 が残存。実装着手可能だが推奨修正あり。
- **REVISE**: P0 が 1 件以上。修正必須。

### 重要度定義

- **P0 (Blocker)**: 未定義だと実装時にエラー・データ破損が確実に発生する欠陥
- **P1 (Important)**: 実装品質に影響するが、実装者が合理的に判断できる余地がある
- **P2 (Nice to have)**: 改善提案。実装を阻害しない

### ルール
- P0 は実装不能な欠陥に限定（スタイル・命名・コメント不足は P0 にしない）
- 前回のレビューで修正済みの項目を再度指摘しないこと
- snippets.md のコードは擬似コードとして扱い、構文の厳密性は検証しないこと

### 出力フォーマット（厳守）
出力の最終行は必ず以下の形式で出力せよ（他のテキストを混ぜない）:
```
VERDICT: APPROVED
```
または
```
VERDICT: CONDITIONAL
```
または
```
VERDICT: REVISE
```
