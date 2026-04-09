---
description: "Phase 2b: plan の Discussion Points を Sonnet subagent で外部技術調査"
---

# Sonnet DP Research — Discussion Points の外部技術調査

plan.md の Discussion Points を Sonnet subagent に委託し、外部知識で補強してください。

## 前提

- `.claude/context/plan.md` が存在し、Discussion Points セクションが含まれていること

## 手順

1. `.claude/context/plan.md` を読み込み、Discussion Points（未解決）セクションを抽出する

2. 各 discussion point について、以下の情報のみを抽出する（暫定判断・採用理由は含めない）:
   - 論点のタイトル
   - 検討した選択肢
   - 各選択肢のトレードオフ（既知のもの）
   - 非機能要件の構造化情報（例: 「ローカルCLI前提」「長時間ジョブあり」「人手介在あり」「コスト重視」等）
     ※ バイアスは増やさず、調査の有効性を上げるため

3. 抽出した情報を `sonnet-dp-research` subagent に渡して調査を委託する

4. subagent の調査結果を `.claude/context/sonnet-dp-research.md` に保存する

5. plan.md を更新する:
   - **subagent は調査のみを行い、plan.md の意思決定（Resolved への移動）は必ず Claude 本体が判断する**。subagent の調査結果に自動追従しない
   - 各 Discussion Point に調査結果を根拠として追記
   - 判断を確定できるものは Discussion Points（未解決）セクションから Resolved セクションに移動
   - 確定できないものは根拠を追記した上で Discussion Points（未解決）に残す

6. ユーザーに結果サマリーを出力:
   - 解決できた論点の数
   - 未解決で残った論点の数
   - 「plan.md を確認し、/codex-plan-review に進んでください」

## 追加コンテキスト（省略可）

$ARGUMENTS

## 注意

- sonnet-dp-research.md は .claude/context/ 配下のローカル作業ファイル（Git 管理しない）
- 調査結果は「外部参考情報」として扱い、プロジェクト固有の制約との整合性は Claude が判断する
- Discussion Points が存在しない場合は「調査対象なし」としてスキップ
