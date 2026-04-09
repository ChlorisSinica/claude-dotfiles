---
description: "§4 Opus↔Codex 2段階クロスレビュー: Phase A（アーキテクチャ）→ Phase B（詳細）"
---

# Codex Plan Review サイクル（2段階）

plan.md と tasks.md の Codex クロスレビューを2段階で実行してください。

## 全体フロー

```
Phase A: アーキテクチャレビュー (max 2 cycles)
  設計前提・API実在性・代替案の検証
  → APPROVED → Phase B へ遷移
  → DISCUSS/REVISE → ユーザー判断 → 修正して再送信 (Phase A 内ループ)

Phase B: 詳細レビュー (max 3 cycles)
  記述品質・整合性・DoD の検証
  → APPROVED → sessions.json 記録して終了
  → DISCUSS/REVISE → 修正して再送信 (Phase B 内ループ)
```

---

## Phase A: アーキテクチャレビュー

### 手順

1. `.claude/context/plan.md` と `.claude/context/tasks.md` を読み込む（`.claude/context/snippets.md` が存在する場合はそれも読み込む）
2. `.claude/agents/prompts/codex_plan_arch_review.md` のプロンプトテンプレートを読み込む
3. テンプレート内のプレースホルダを置換:
   - `$FEATURE`: `$ARGUMENTS` が空なら plan.md の Objective から推定
   - `$USER_REQUEST`: `.claude/context/plan.md` の作成時に `/plan` に渡された元のユーザー要望テキスト。plan.md の冒頭コメントや git log から取得。取得できない場合は `$FEATURE` と同じ値を使用。
4. プロンプトと plan.md/tasks.md/snippets.md を結合し `.claude/context/_codex_input.tmp` に書き出す

5. **サイクル2: 前回指摘の注入**
   - `.claude/context/codex_plan_arch_review.md`（前回の Phase A 出力）が存在し、かつサイクル1でない場合:
   - `_codex_input.tmp` の末尾に以下を追加:
     ```
     ---
     # Previous Architecture Review (Cycle N-1)
     以下は前回サイクルの指摘事項です。修正が適切に行われたか検証してください。
     <前回の codex_plan_arch_review.md の内容>
     ```
   - サイクル1では追加しない（白紙で開始）

6. Codex に送信:
```bash
cat .claude/context/_codex_input.tmp | codex review -
```

7. Codex の出力を `.claude/context/codex_plan_arch_review.md` に保存（毎サイクル上書き）

### Phase A の終了条件

1. Codex が **APPROVED** を返した → **Phase B に遷移**
2. Codex が **DISCUSS** を返した → 議論内容をユーザーに提示し判断を仰ぐ
   - 懸念の中に「技術選定の根拠不足」「外部情報で解決可能な疑問」が含まれる場合:
     → Codex の新論点を plan.md の Discussion Points（未解決）セクションに追記する
     → 「/sonnet-dp-research で追加調査しますか？」をユーザーに提案
   - ユーザーの判断に従い、修正後に再送信
3. Codex が **REVISE** を返した → ユーザーに状況報告し判断を仰ぐ。修正後に再送信
4. **2サイクル到達** → ユーザーに状況報告し判断を仰ぐ
5. Codex API エラー → ユーザーに報告し待機

### Phase A 各サイクルの進め方

1. Codex の出力を受信し `.claude/context/codex_plan_arch_review.md` に保存
2. **ユーザーへサマリーを出力**（判定結果、Assumptions to verify / Architecture risks / Simpler alternative の要約）
3. DISCUSS の場合: ユーザーに提示し判断を仰ぐ → 方針決定後に修正
4. REVISE の場合: ユーザーに提示し判断を仰ぐ → 方向転換を反映
5. 修正後、再送信

---

## Phase B: 詳細レビュー

### Phase B 開始条件

- Phase A で **APPROVED** を取得済みであること

### 手順

1. `.claude/context/plan.md` と `.claude/context/tasks.md` を読み込む（`.claude/context/snippets.md` が存在する場合はそれも読み込む）
2. `.claude/agents/prompts/codex_plan_review.md` のプロンプトテンプレートを読み込む
3. テンプレート内のプレースホルダを置換（Phase A と同じ）
4. プロンプトと plan.md/tasks.md/snippets.md を結合し `.claude/context/_codex_input.tmp` に書き出す

5. **サイクル2以降: 前回指摘の注入**
   - `.claude/context/codex_plan_tasks_review.md`（前回の Phase B 出力）が存在し、かつサイクル1でない場合:
   - `_codex_input.tmp` の末尾に以下を追加:
     ```
     ---
     # Previous Detail Review (Cycle N-1)
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

### Phase B の終了条件

1. Codex が **APPROVED** を返した → `.claude/agents/sessions.json` に記録してサイクル終了:
   - sessions.json を読み込み、`reviews` キーがなければ `{"reviews": []}` で初期化する
   - `reviews` 配列に追記:
   ```json
   {"kind": "plan-review", "phase_a_cycles": <Phase Aのサイクル数>, "phase_b_cycles": <Phase Bのサイクル数>, "date": "<ISO8601>", "verdict": "APPROVED", "session_id": "<Codex session ID>"}
   ```
2. Codex が **DISCUSS** を返した → 議論内容をユーザーに提示し判断を仰ぐ
3. Codex が **REVISE** を返した → 記述を修正して再送信
4. **3サイクル到達** → ユーザーに状況報告し判断を仰ぐ
5. Codex API エラー → ユーザーに報告し待機

### Phase B 各サイクルの進め方

1. Codex の出力を受信し `.claude/context/codex_plan_tasks_review.md` に保存
2. **ユーザーへサマリーを出力**（判定結果、主要な指摘のリスト）
3. DISCUSS の場合: ユーザーに提示し判断を仰ぐ → 方針決定後に修正
4. REVISE の場合: 記述を修正して再送信
5. 修正後、再送信

---

## 重要ルール

- Codex は技術パートナーであり、門番ではない — APPROVED を出し渋る必要はない
- Phase A と Phase B の指摘を混在させない — Phase A は設計のみ、Phase B は詳細のみ
- 前回指摘の注入はフェーズ内に限定する（Phase A の指摘を Phase B に注入しない）
- レビュー結果は各フェーズの出力ファイルを上書き更新する:
  - Phase A: `.claude/context/codex_plan_arch_review.md`
  - Phase B: `.claude/context/codex_plan_tasks_review.md`
- snippets.md のコードは擬似コードとして扱い、構文の厳密性は検証しないこと

## 注意

- `.claude/context/` 配下のファイル（plan.md, tasks.md, snippets.md, codex_plan_arch_review.md, codex_plan_tasks_review.md）は **Git 管理しない**（ローカル作業ファイル）
- 自動コミット・プッシュは行わない
