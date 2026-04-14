---
name: sonnet-dp-research-bridge
description: "未解決の Discussion Point を Claude / Sonnet に手動委譲するための中立な調査ブリーフを作る。設計論点が外部情報、ベンダー比較、時変な製品挙動、あるいは Codex 本体の実装フロー外で行うべきベストプラクティス調査に依存するときに使う。"
---

# Sonnet DP Research Bridge

`.claude/` の runtime file を生成せずに、Claude / Sonnet 向けの調査ブリーフを整える。

## Workflow

1. `.agents/context/plan.md` から未解決の Discussion Point を読む。
2. `.agents/templates/sonnet-dp-research-input.md` を埋める。
3. `.agents/prompts/sonnet-dp-research.md` を Claude / Sonnet への handoff prompt として使う。
4. 返ってきた調査結果を `.agents/context/sonnet-dp-research.md` に保存する。
5. plan 更新時の根拠として使う。

## Rules

- ブリーフは中立に保つ。
- 評価軸や制約は渡すが、答えを先回りして決めない。
- 時変情報が絡む論点では、日付つきの一次情報と鮮度メモを必須にする。
