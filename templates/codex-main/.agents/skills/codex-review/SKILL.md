---
name: codex-review
description: "plan または実装を単発でレビューし、所見を `.agents/reviews/` に保存する。`codex-plan-review` や `codex-impl-review` ほど厳密なサイクルは不要だが、後続で参照できるレビュー記録が欲しいときに使う。"
---

# Codex Review

焦点を絞ったレビューを行い、結果を後で再利用できる形で保存する。

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

- 結果は `.agents/reviews/` に保存する
- `plan-review.md` または `impl-review.md` を優先する
- findings を重大度順に先頭へ並べる
- 重大な問題がなければその旨を明記し、残るリスクを短く添える
