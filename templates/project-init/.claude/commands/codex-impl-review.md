---
description: "§5 実装レビュー: 修正ファイル+依存ファイルを Codex の厳格レビュアーに送信"
---

# Codex Implementation Review

実装の Codex 厳格レビューを実行してください。
**APPROVED が出るまで自律的にサイクルを回すこと。途中でユーザーに判断を仰がない。**

## 入力

- `$ARGUMENTS`: タスク説明と対象ファイルパス（カンマ区切り）
  - 例: `ユーザー認証の修正, src/auth.py, src/middleware.py`
  - 空の場合: 直近の `git diff --name-only` から対象ファイルを自動検出

## 手順

1. 対象ファイルを特定:
   - `$ARGUMENTS` が指定されていればそこからタスク説明とファイルリストを取得
   - 空の場合: `git diff --name-only` で変更ファイル一覧を取得

2. `.claude/agents/prompts/codex_impl_review.md` のプロンプトテンプレートを読み込む

3. テンプレートのプレースホルダを置換:
   - `$TASK_DESCRIPTION` → タスク説明
   - `$FILE_LIST` → 対象ファイルのパス一覧

4. 対象ファイルと依存ファイルの内容を収集・結合し `.claude/context/_codex_input.tmp` に書き出す。
   加えて、存在すれば以下も bundle に含める（plan / 実装 mismatch 検出のため）:
   - `.claude/context/plan.md`: plan と実装の整合性チェック用
   - `.claude/context/tasks.md`: current task / slice の範囲確認用
   - `.claude/context/implementation_gap_audit.md`: 既知の plan vs 実装差分があれば注入
   - workflow / hotkey / lifecycle / state-machine / GUI 変更では上記 3 つを原則として含める

5. **サイクル2以降: 前回指摘の注入**
   - `.claude/context/codex_impl_review.md`（前回の Codex 出力）が存在し、かつサイクル1でない場合:
   - `_codex_input.tmp` の末尾に以下を追加:
     ```
     ---
     # Previous Review (Cycle N-1)
     以下は前回サイクルの指摘事項です。修正が適切に行われたか検証してください。
     <前回の codex_impl_review.md の内容>
     ```
   - サイクル1では追加しない（白紙で開始）

6. Codex に送信:
```bash
cat .claude/context/_codex_input.tmp | codex review -
```

7. **Codex 出力を `.claude/context/codex_impl_review.md` に保存する**（毎サイクル上書き）

8. 出力の最終行から判定をパースする（`VERDICT: APPROVED` 等）:
   - **APPROVED** → サイクル終了。ユーザーに報告
   - **CONDITIONAL** → 未解決 P0/P1 があれば自律修正し、再送信（手順4に戻る）。ただし current slice の P0/P1 が 0 で、残件が slice 外の migration hygiene / cleanup / residual risk のみなら、follow-up task を `.claude/context/tasks.md` に追記した上で **APPROVED 相当**として扱いサイクル終了
   - **REVISE** → P0/P1 を自律修正し、再送信（手順4に戻る）
   - 判定行が見つからない場合 → CONDITIONAL として扱う

9. APPROVED 取得後、`.claude/agents/sessions.json` に記録:
   - sessions.json を読み込み、`reviews` キーがなければ `{"reviews": []}` で初期化する
   - `reviews` 配列に追記:
   ```json
   {"kind": "impl-review", "cycle": <現在のサイクル番号>, "date": "<ISO8601>", "verdict": "APPROVED", "session_id": "<Codex session ID>"}
   ```

## スコープ

- review の主対象は「今回の task / task-description で宣言した current slice」とその直接依存に限定する
- current slice 外の既存 install / legacy / 旧 repo 全体の完全収束や完全 cleanup は、既定では主対象にしない
- fresh scaffold / declared dogfood scope / 生成された runner の直接動作確認が済んでいる場合、pre-history migration hygiene は default では追わない

## 終了条件

1. Codex が **APPROVED** を返した → サイクル終了
2. Codex が **CONDITIONAL** で、残件が current slice 外の migration hygiene / cleanup / residual risk のみ → follow-up task を `.claude/context/tasks.md` に追記した上で **APPROVED 相当**としてサイクル終了
3. **同種の指摘が 2 回連続**し、current slice の correctness evidence は既に揃っている → residual risk として follow-up task 化し、rerun より停止判断を優先して次 task / 人間判断へ進む
4. **5サイクル到達** → ユーザーに状況報告し判断を仰ぐ（これが唯一のユーザー確認ポイント）
5. **同種失敗が3回**続いた → 停止し `.claude/context/failure_report.md` に詳細を記録
6. Codex API エラー → ユーザーに報告し待機

## 重要ルール

- **APPROVED または APPROVED 相当が出るまで自律的に回し続ける**。CONDITIONAL は未解決 P0/P1 があれば修正して再送信。ただし残件が current slice 外の follow-up のみなら APPROVED 相当として終了してよい
- レビュー結果は毎回ユーザーへ要点サマリーを出力（判定結果、P0/P1/P2 件数、主要指摘）
- **Severity 較正**: migration hygiene / legacy cleanup / 完全収束要求は、current slice の correctness を直接壊す場合だけ P1 として扱う。単なる完全性要求は follow-up task へ落とし、rerun を伸ばさない
- **同種指摘の扱い**: 同じ指摘が 2 回連続で出た場合、current slice の correctness evidence が揃っているなら rerun より follow-up task 化と residual risk 明示を優先する

## コミット

APPROVED 取得後、`/implement` から呼ばれた場合は `/implement` 側のコミット手順に従う。
単独で呼ばれた場合:

1. `git diff --name-only` で変更ファイル一覧を取得
2. **ソースコードの変更のみ** `git add`（`.claude/context/` 配下は Git 管理しない）
3. コミットメッセージ: `fix: apply codex-impl-review fixes`
4. プッシュはユーザーに確認してから行う

**Co-Authored-By**: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` をコミットメッセージ末尾に付与。
