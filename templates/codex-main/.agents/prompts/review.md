# レビュープロンプト

Codex の plan review や implementation review を行うときに使う。

## 入力に含めるもの

- `.agents/AGENTS.md`
- `.agents/context/` の関連ファイル
- 変更されたソースファイルまたは diff
- 再レビュー時は `.agents/reviews/` の既存レビュー結果

## レビュー優先度

- 正しさ
- 振る舞いの後方互換性
- データフロー破壊
- 検証不足
- 隠れた前提

## 出力

レビュー結果は `.agents/reviews/` に保存する。
推奨ファイル:

- `plan-review.md`
- `impl-review.md`

findings を重大度順に先頭へ並べる。
