---
name: codex-impl-review
description: "実装済みの変更を Codex の厳格レビュアーに送り、APPROVED まで再レビューを回す。最終実装の欠陥を潰したいとき、まとめてレビュー記録を残したいときに使う。"
---

# Codex Implementation Review

変更済みファイルを Codex の厳格レビュアーに送り、APPROVED まで再レビューする。

## Workflow

1. 対象ファイルを決める。明示指定があればそれを優先し、なければ `git diff --name-only` で変更ファイルを取る。
2. タスク説明は明示引数を優先し、なければ直近の変更内容から短く要約する。
3. review runner は `pwsh` で実行する。Windows PowerShell 5.1 ではなく `pwsh -NoProfile -ExecutionPolicy Bypass -File ...` を正規経路にする。
4. `.agents/prompts/codex_impl_review.md` を読む。
5. まず `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-codex-impl-review.ps1` を使う。ad hoc な長い 1 行コマンドや一時 `_tmp` スクリプトは避ける。
6. 必要なら `-TaskDescription`、`-Files`、`-IncludeFiles` を渡す。依存ファイルを明示したいときは `-IncludeFiles` を使う。
7. runner は prompt, タスク説明, 対象ファイル一覧, 関連 diff, 必要な依存ファイル内容を `.agents/context/_codex_input.tmp` にまとめ、前回結果が `.agents/context/codex_impl_review.md` にあれば末尾へ注入する。
8. runner は `codex review -` を実行し、出力を `.agents/context/codex_impl_review.md` と `.agents/reviews/impl-review.md` に保存する。
9. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗で止まった場合は、`.agents/prompts/codex_impl_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。
10. 手動レビューでも判定は `APPROVED` / `CONDITIONAL` / `REVISE` 相当で扱い、結果と修正内容を `.agents/context/codex_impl_review.md` または `.agents/reviews/impl-review.md` に残す。
11. `VERDICT:` と `Cycle:` を確認する。`VERDICT: APPROVED` 相当なら終了する。
12. `CONDITIONAL` / `REVISE` なら P0/P1 を優先して修正し、ユーザーへ戻らず即 rerun する。
13. 同種失敗が 3 回続く場合は `.agents/context/failure_report.md` に切り出す。
14. runner は `.agents/reviews/sessions.json` に cycle 数を残すので、停止判断にはそれも使う。

## ルール

- 変更は局所的に保ち、レビューを通すためだけの無関係な掃除をしない。
- `APPROVED` が出るまで回すが、最大サイクル数を超えたら要点をまとめて人間へ返す。
- レビュー入力には、変更箇所だけでなく依存先とデータフローの文脈を最低限含める。
- 中間ファイルは `.agents/context/codex_impl_review.md` に置き、`.agents/reviews/impl-review.md` は共有しやすい要約版として扱う。
- 最大 5 サイクルを目安にし、超える場合は blocker と未解決論点をまとめて人間へ返す。
- runner が作る `.agents/context/_codex_input.tmp` をそのまま再利用し、別の補助スクリプトを増やさない。
- `CONDITIONAL` / `REVISE` のたびに止まらず、自分で修正して再レビューまで進める。
