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
   - 意思決定時に重視したい評価軸（例: 信頼性、可搬性、運用負荷、導入容易性、ベンダーロックイン、コスト）
     ※ 「どの案を採るべきか」は渡さず、「何を重視して比較するか」だけを渡す
   - time-sensitive な外部事実を含むかどうか
   - 関係するベンダー / プロダクト surface（例: ChatGPT / API / Enterprise, browser app / desktop app）

3. 抽出した情報を `sonnet-dp-research` subagent に渡して調査を委託する
   - time-sensitive な論点では「公式ソース優先」「日付必須」「surface を分離して比較」を明示する
   - time-sensitive な論点では、各出典について公開日または更新日を必ず記録させる
   - 新しい公式ソースが見つからず古い一次情報しかない場合は、その旨を stale candidate として明記させる
   - 「latest / current / today」に相当する主張は、日付付き一次ソースで確認できない限り断定しないよう指示する

4. subagent の調査結果を `.claude/context/sonnet-dp-research.md` に保存する

5. plan.md を更新する:
   - **subagent は調査のみを行い、plan.md の意思決定（Resolved への移動）は必ず Claude 本体が判断する**。subagent の調査結果に自動追従しない
   - 各 Discussion Point に調査結果を根拠として追記
   - time-sensitive な論点は、日付付きの公式ソースで裏取りでき、かつ freshness が十分な場合のみ判断を強める
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
- モデル名、料金、提供状況、サポート状況など変化しやすい情報は stale になりやすいため、ベンダー公式ソースと確認日を必須とする
- 新しい一次情報が見つからず古い一次情報しか取れない場合は、そのまま採用根拠にせず「古い一次情報のみ」と明記する
