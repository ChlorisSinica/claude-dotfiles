---
name: codex-implement
description: "`.agents/context/tasks.md` の次の未完了タスクを、局所的な変更と逐次検証で実行する。計画が固まり、実装を小さく検証可能な単位で進めたいとき、plan / implementation drift や verify wrapper failure が起きる repo で mismatch audit と fallback verification を挟みながら進めたいときに使う。"
---

# Codex Implement

計画済みの作業を、検証を密に保ちながら段階的に実装する。

## Workflow

1. `.agents/context/tasks.md` を読む。workflow-heavy な変更や既知の mismatch がある場合は `.agents/context/plan.md` と `.agents/context/implementation_gap_audit.md` も読む。
2. 次の未完了タスクを選ぶ。ただし plan / implementation drift、古い task wording、実装順の前提崩れを見つけた場合は、その audit を先に行ってよい。
3. 新しい mismatch を見つけた場合は、作業続行前に `.agents/context/implementation_gap_audit.md` を作成または更新して既知差分を明文化する。
4. そのタスクを満たす最小限で安全な変更を入れる。
5. タスク固有の検証があれば実行する。
6. プロジェクト全体検証は repo 付属の verify wrapper を優先する。`pwsh` 系では `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-verify.ps1`、bash 系では `./scripts/run-verify.sh` を使う。
7. verify wrapper 自体が quoting / environment / compatibility の問題で壊れている場合は、その failure mode を `.agents/context/failure_report.md` に残し、`.agents/AGENTS.md` にある最小の直接検証へ切り替える。wrapper failure だけでコード不良と断定しない。
8. 検証が通ってからタスクを完了扱いにする。残るリスクがある場合は task または audit に明示する。
9. 意味のある実装単位がまとまったら `codex-impl-review` に回せるよう差分と文脈を整理する。workflow-heavy な変更では `plan.md`、`tasks.md`、`implementation_gap_audit.md` を review 入力に含める前提で整える。

## ルール

- 編集は局所的に保つ。
- 無関係なリファクタを避ける。
- インターフェースやデータフローを変えたら、上流と下流の影響を確認する。
- workflow や task の意味が変わったら、stale な task wording や obsolete な前提を残さない。
- 同じ失敗が繰り返される場合は `.agents/templates/failure_report.md` を `.agents/context/failure_report.md` にコピーして埋める。
- recovery や alignment を多く含む長いサイクルになった場合は、`handover-skills` があれば handover artifact を更新してから閉じる。
