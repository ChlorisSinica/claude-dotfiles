---
name: codex-plan
description: "機能追加や不具合修正の依頼を、`.agents/context/plan.md` と `.agents/context/tasks.md` に落とし込む具体的な実装計画へ変換する。実装前に設計したいとき、スコープ整理が必要なとき、複数ファイルやデータフローに影響が及ぶときに使う。"
---

# Codex Plan

依頼内容を、実装開始前にレビュー可能な計画へ変換する。

## Workflow

1. `.agents/context/research.md` があれば最初に読む。
2. 目的と成功条件を定義する。
3. 非目標とリスクを整理する。
4. 影響するファイル、インターフェース、データフローを洗い出す。
5. 検証可能な DoD 付きのタスクリストを書く。
6. 出力先:
   - `.agents/context/plan.md`
   - `.agents/context/tasks.md`
   - 擬似コードが有効なら `.agents/context/snippets.md`
7. 計画が書けたら `codex-plan-review` に回せる状態まで整える。

## plan に必ず含めるもの

- 目的と成功条件
- 非目標
- 技術方針と代替案
- 影響ファイル
- データフローへの影響
- リスクとロールバック方針
- 検証戦略
- 未解決の設計論点（Discussion Points）

## ルール

- plan 中に実装しない。
- 具体的なファイルパスと検証可能なタスクを優先する。
- 外部事実に依存する設計論点は Discussion Points に残し、必要なときだけ Sonnet bridge に渡す。
