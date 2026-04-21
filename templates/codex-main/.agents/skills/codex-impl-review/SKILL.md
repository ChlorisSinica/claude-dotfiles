---
name: codex-impl-review
description: "実装済みの変更を Codex の厳格レビュアーに送り、品質・整合性・recovery を切り分けながら収束するまで再レビューする。workflow / state-machine / hotkey / lifecycle 変更や大規模実装で、固定サイクル数ではなく verdict・failure mode・implementation gap audit・handover 条件に基づいて停止判断したいときに使う。"
---

# Codex Implementation Review

変更済みファイルを Codex の厳格レビュアーに送り、品質・整合性・recovery を切り分けながら収束するまで再レビューする。

## Workflow

1. 対象ファイルを決める。明示指定があればそれを優先し、なければ `git diff --name-only` で変更ファイルを取る。
2. タスク説明は明示引数を優先し、なければ直近の変更内容から短く要約する。
3. workflow / hotkey / lifecycle / state-machine / control-flow の変更、または plan / implementation mismatch のリスクがあるか先に判定する。該当する場合は `plan.md`、`tasks.md`、既存の `implementation_gap_audit.md`、必要な review artifact を review 入力に含める前提で進める。
4. review runner は Python で実行する。`Python 3.11+` の実行可能ランタイムを正規経路にする。
5. `.agents/prompts/codex_impl_review.md` を読む。
6. まず `{{PYTHON_LAUNCHER}} scripts/run-codex-impl-review.py` を使う。ad hoc な長い 1 行コマンドや一時 `_tmp` スクリプトは避ける。長時間 review で待ち時間を延ばしたい場合だけ `--review-timeout-sec <seconds>` を付ける。既定は 600 秒。
7. 必要なら `--task-description`、`--files`、`--include-files` を渡す。workflow-heavy な変更では `plan.md`、`tasks.md`、`implementation_gap_audit.md`、主要な依存ファイルを優先して `--include-files` に入れる。
8. runner は prompt, タスク説明, 対象ファイル一覧, 関連 diff, 必要な依存ファイル内容を `.agents/context/_codex_input.tmp` にまとめ、前回結果が `.agents/context/codex_impl_review.md` にあれば末尾へ注入する。
9. runner は `codex review -` を実行し、出力を `.agents/context/codex_impl_review.md` と `.agents/reviews/impl-review.md` に保存する。
10. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗、runner 互換不良で止まった場合は、`.agents/prompts/codex_impl_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。`Failure mode:` は `permission-denied` / `empty-output` / `environment` / `runner-compat` / `unknown` の固定ラベルで残す。
11. 手動レビューでも判定は `APPROVED` / `CONDITIONAL` / `REVISE` 相当で扱う。各記録には必要に応じて `Cycle type:` を `quality` / `alignment` / `recovery` / `decision` のいずれかで残す。
12. `VERDICT:` を確認する。`VERDICT: APPROVED`、または `current slice` の未解決 P0/P1 が 0 で残りが follow-up task 化済みの migration hygiene / cleanup completeness / residual risk だけの `CONDITIONAL` なら終了してよい。
13. それ以外の `CONDITIONAL` / `REVISE` なら P0/P1 を優先して修正し、ユーザーへ戻らず即 rerun する。各 rerun は、重要欠陥、plan / implementation mismatch、または verification risk を実質的に減らせるときだけ続ける。
14. review 中に新しい plan / implementation mismatch を見つけた場合は、続行前に `.agents/context/implementation_gap_audit.md` を作成または更新し、既知差分を明文化する。
15. 同じ failure mode や同じ unresolved blocker が 3 回続いても新しい情報が増えない場合は `.agents/context/failure_report.md` に切り出し、人間へ返す。
16. runner は `.agents/reviews/sessions.json` に cycle 数を残すが、これは停止条件ではなく観測値として扱う。

## Scope And Stop Conditions

- review の主対象は `今回の task / milestone / task-description で宣言した current slice` と、その slice の直接依存に限定する。
- fresh scaffold、declared dogfood scope、generated runner の直接動作確認が済んでいる場合、`既存 install 全体の完全収束`、`旧 repo 全部の完全 cleanup`、`pre-history migration hygiene` は既定では主対象にしない。
- `current slice` に対する未解決の `P0/P1` が 0 で、残りが migration completeness や cleanup completeness のみなら、`APPROVED` 相当として task 化して cycle を抜けてよい。
- 同種の migration hygiene 指摘が 2 回連続し、current slice の correctness evidence が増えている場合は、追加 rerun ではなく residual risk または follow-up task として扱う。
- review が `fresh path は通るが legacy convergence の完全性をさらに求める` 段階に入ったら、無限 rerun を避けるため停止判断を優先する。

## Out Of Scope By Default

- wrapper / alias / legacy `.ps1` 互換の維持
- 明示 task に入っていない既存 install 全体の完全 cleanup
- 明示 task に入っていない既存 repo 全体の完全 cleanup
- review を通すためだけの包括的な migration hygiene 最適化

## ルール

- 変更は局所的に保ち、レビューを通すためだけの無関係な掃除をしない。
- `APPROVED` を終了条件に置くが、停止判断は固定サイクル数ではなく、改善の有無、failure mode、人間判断の要否、review 単位の適切さで行う。`CONDITIONAL` でも残件が slice 外 follow-up のみなら `APPROVED` 相当として扱ってよい。
- レビュー入力には、変更箇所だけでなく依存先とデータフローの文脈を最低限含める。workflow-heavy な変更では `plan.md`、`tasks.md`、`implementation_gap_audit.md` を原則として含める。
- 中間ファイルは `.agents/context/codex_impl_review.md` に置き、`.agents/reviews/impl-review.md` は共有しやすい要約版として扱う。
- cycle 数は観測値であり、主ルールにしない。
- 各 cycle で新しい高重要度の欠陥が減っている、alignment が改善している、または recovery で unblock できている限りは継続してよい。
- 同種指摘が減らずに反復する、残件が人間の優先度判断待ちになる、review 対象が広すぎて分割したほうがよい場合は、要点をまとめて人間へ返す。
- migration hygiene 指摘は、`current slice` の correctness を直接壊す場合だけ `P1` として扱う。単なる完全収束要求は follow-up task へ落としてよい。
- runner が作る `.agents/context/_codex_input.tmp` をそのまま再利用し、別の補助スクリプトを増やさない。
- manual fallback では `Failure mode:` を固定ラベルで残し、`quality` と `recovery` を混同しない。
- 長い review が `recovery` や `alignment` cycle を多く含んだ場合は、repo に `handover-skills` があれば handover artifact を更新してから閉じる。
- `CONDITIONAL` / `REVISE` のたびに止まらず、自分で修正して再レビューまで進める。
