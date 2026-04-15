---
name: codex-implement
description: "`.agents/context/tasks.md` の次の未完了タスクを、局所的な変更と逐次検証で実行する。計画が固まり、実装を小さく検証可能な単位で進めたいときに使う。"
---

# Codex Implement

計画済みの作業を、検証を密に保ちながら段階的に実装する。

## Workflow

1. `.agents/context/tasks.md` を読む。
2. 次の未完了タスクを選ぶ。
3. そのタスクを満たす最小限で安全な変更を入れる。
4. タスク固有の検証があれば実行する。
5. プロジェクト全体検証は repo 付属の verify wrapper を優先する。`pwsh` 系では `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-verify.ps1`、bash 系では `./scripts/run-verify.sh` を使う。
6. `.agents/AGENTS.md` のプロジェクト全体検証を実行する。
7. 検証が通ってからタスクを完了扱いにする。
8. 意味のある実装単位がまとまったら `codex-impl-review` に回せるよう差分と文脈を整理する。

## ルール

- 編集は局所的に保つ。
- 無関係なリファクタを避ける。
- インターフェースやデータフローを変えたら、上流と下流の影響を確認する。
- 同じ失敗が繰り返される場合は `.agents/templates/failure_report.md` を `.agents/context/failure_report.md` にコピーして埋める。
