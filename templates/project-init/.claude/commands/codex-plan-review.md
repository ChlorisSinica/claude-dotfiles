---
description: "§4 Opus↔Codex クロスレビューサイクル: plan.md/tasks.md を Codex でレビュー→修正→再レビュー"
---

# Codex Plan Review サイクル

plan.md と tasks.md の Codex クロスレビューを実行してください。

## 手順

1. `.claude/context/plan.md` と `.claude/context/tasks.md` を読み込む（`.claude/context/snippets.md` が存在する場合はそれも読み込む）
2. `.claude/agents/prompts/codex_plan_review.md` のプロンプトテンプレートを読み込む
3. テンプレート内のプレースホルダを置換:
   - `$FEATURE`: `$ARGUMENTS` が空なら plan.md の Objective から推定
   - `$USER_REQUEST`: `.claude/context/plan.md` の作成時に `/plan` に渡された元のユーザー要望テキスト。plan.md の冒頭コメントや git log から取得。取得できない場合は `$FEATURE` と同じ値を使用。
4. プロンプトと plan.md/tasks.md/snippets.md を結合し `.claude/context/_codex_input.tmp` に書き出す

5. **サイクル2以降: 前回指摘の注入**
   - `.claude/context/codex_plan_tasks_review.md`（前回の Codex 出力）が存在し、かつサイクル1でない場合:
   - `_codex_input.tmp` の末尾に以下を追加:
     ```
     ---
     # Previous Review (Cycle N-1)
     以下は前回サイクルの指摘事項です。修正が適切に行われたか検証してください。
     <前回の codex_plan_tasks_review.md の内容>
     ```
   - サイクル1では追加しない（白紙で開始）

6. Codex に送信:
```bash
cat .claude/context/_codex_input.tmp | codex review -
```

7. Codex の出力を `.claude/context/codex_plan_tasks_review.md` に保存（毎サイクル上書き）
8. レビュー指摘を分析し、plan.md / tasks.md / snippets.md を修正
9. 修正後、再度 Codex にレビューを送信（手順4に戻る）
10. Codex から指摘がなくなるまでサイクルを繰り返す

## 終了条件

1. Codex が **APPROVED** を返した → サイクル終了
2. Codex が **DISCUSS** を返した → 議論内容をユーザーに提示し判断を仰ぐ。ユーザーが合意すれば plan を修正して再送信、問題なしと判断すれば終了
3. Codex が **REVISE** を返した → 根本的な設計変更を検討。plan を修正して再送信
4. **3サイクル到達** → ユーザーに状況報告し判断を仰ぐ
5. Codex API エラー → ユーザーに報告し待機

## 各サイクルの進め方

1. Codex の出力を受信し `.claude/context/codex_plan_tasks_review.md` に保存
2. **ユーザーへサマリーを出力**（判定結果、主要な議論点・質問・懸念のリスト）
3. DISCUSS の場合: Codex の質問・懸念をユーザーと議論し、方針を決定してから修正
4. REVISE の場合: 懸念箇所の影響を plan.md/tasks.md 全体で確認し、方針転換を反映
5. 修正後、再送信

## 重要ルール

- Codex は技術パートナーであり、門番ではない — APPROVED を出し渋る必要はない
- 議論の目的は「欠陥を見つけること」ではなく「より良い設計を見つけること」
- レビュー結果は毎回 `.claude/context/codex_plan_tasks_review.md` を上書き更新する
- snippets.md のコードは擬似コードとして扱い、構文の厳密性は検証しないこと

## 注意

- `.claude/context/` 配下のファイル（plan.md, tasks.md, snippets.md, codex_plan_tasks_review.md）は **Git 管理しない**（ローカル作業ファイル）
- 自動コミット・プッシュは行わない
