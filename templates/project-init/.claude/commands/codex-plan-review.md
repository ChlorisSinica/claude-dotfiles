---
description: "§4 Opus↔Codex クロスレビューサイクル: plan.md/tasks.md を Codex でレビュー→修正→再レビュー"
---

# Codex Plan Review サイクル

plan.md と tasks.md の Codex クロスレビューを実行してください。

## 手順

1. `.context/plan.md` と `.context/tasks.md` を読み込む（`.context/snippets.md` が存在する場合はそれも読み込む）
2. `.agents/prompts/codex_plan_review.md` のプロンプトテンプレートを読み込む
3. テンプレート内のプレースホルダを置換:
   - `$FEATURE`: `$ARGUMENTS` が空なら plan.md の Objective から推定
   - `$USER_REQUEST`: `.context/plan.md` の作成時に `/plan` に渡された元のユーザー要望テキスト。plan.md の冒頭コメントや git log から取得。取得できない場合は `$FEATURE` と同じ値を使用。
4. プロンプトと plan.md/tasks.md/snippets.md を結合し `.context/_codex_input.tmp` に書き出す

5. **サイクル2以降: 前回指摘の注入**
   - `.context/codex_plan_tasks_review.md`（前回の Codex 出力）が存在し、かつサイクル1でない場合:
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
cat .context/_codex_input.tmp | codex review -
```

7. Codex の出力を `.context/codex_plan_tasks_review.md` に保存（毎サイクル上書き）
8. レビュー指摘を分析し、plan.md / tasks.md / snippets.md を修正
9. 修正後、再度 Codex にレビューを送信（手順4に戻る）
10. Codex から指摘がなくなるまでサイクルを繰り返す

## 終了条件

1. Codex が **APPROVED** を返した → サイクル終了
2. Codex が **CONDITIONAL** を返した → P1 を確認し、対応不要と判断すれば終了可
3. **5サイクル到達** → ユーザーに状況報告し判断を仰ぐ
4. Codex API エラー → ユーザーに報告し待機

## 修正プロセス（各サイクル）

1. Codex レビュー結果を受信・保存
2. **ユーザーへ要点サマリーを出力**（判定結果、P0件数、主要指摘のリスト）
3. 修正前に: 各指摘の影響箇所を plan.md/tasks.md/snippets.md 全体で grep
4. 影響箇所リストを作成してから一括修正
5. 修正後、整合性を確認
6. 再送信

## 重要ルール

- サイクルの終了を Codex に催促しない
- 抜け目なく妥協なくサイクルを繰り返す
- レビュー結果は毎回 `.context/codex_plan_tasks_review.md` を上書き更新する
- snippets.md のコードは擬似コードとして扱い、構文の厳密性は検証しないこと

## 自動コミット & プッシュ

APPROVED または CONDITIONAL（P0=0 で終了判断）でサイクル終了後:

1. `git add .context/plan.md .context/tasks.md .context/snippets.md .context/codex_plan_tasks_review.md`（存在するファイルのみ）
2. コミットメッセージ: `docs: update plan.md + tasks.md (codex-plan-review APPROVED/CONDITIONAL)`
3. `git push`
4. コミット・プッシュ完了をユーザーに報告

**Co-Authored-By**: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` をコミットメッセージ末尾に付与。
