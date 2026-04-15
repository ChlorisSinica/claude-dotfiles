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
4. review runner は `pwsh` で実行する。Windows PowerShell 5.1 ではなく `pwsh -NoProfile -ExecutionPolicy Bypass -File ...` を正規経路にする。
5. `.agents/prompts/codex_impl_review.md` を読む。
6. まず `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-codex-impl-review.ps1` を使う。ad hoc な長い 1 行コマンドや一時 `_tmp` スクリプトは避ける。
7. 必要なら `-TaskDescription`、`-Files`、`-IncludeFiles` を渡す。workflow-heavy な変更では `plan.md`、`tasks.md`、`implementation_gap_audit.md`、主要な依存ファイルを優先して `-IncludeFiles` に入れる。
8. runner は prompt, タスク説明, 対象ファイル一覧, 関連 diff, 必要な依存ファイル内容を `.agents/context/_codex_input.tmp` にまとめ、前回結果が `.agents/context/codex_impl_review.md` にあれば末尾へ注入する。
9. runner は `codex review -` を実行し、出力を `.agents/context/codex_impl_review.md` と `.agents/reviews/impl-review.md` に保存する。
10. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗、runner 互換不良で止まった場合は、`.agents/prompts/codex_impl_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。`Failure mode:` は `permission-denied` / `empty-output` / `environment` / `runner-compat` / `unknown` の固定ラベルで残す。
11. 手動レビューでも判定は `APPROVED` / `CONDITIONAL` / `REVISE` 相当で扱う。各記録には必要に応じて `Cycle type:` を `quality` / `alignment` / `recovery` / `decision` のいずれかで残す。
12. `VERDICT:` を確認する。`VERDICT: APPROVED` 相当なら終了する。
13. `CONDITIONAL` / `REVISE` なら P0/P1 を優先して修正し、ユーザーへ戻らず即 rerun する。各 rerun は、重要欠陥、plan / implementation mismatch、または verification risk を実質的に減らせるときだけ続ける。
14. review 中に新しい plan / implementation mismatch を見つけた場合は、続行前に `.agents/context/implementation_gap_audit.md` を作成または更新し、既知差分を明文化する。
15. 同じ failure mode や同じ unresolved blocker が 3 回続いても新しい情報が増えない場合は `.agents/context/failure_report.md` に切り出し、人間へ返す。
16. runner は `.agents/reviews/sessions.json` に cycle 数を残すが、これは停止条件ではなく観測値として扱う。

## ルール

- 変更は局所的に保ち、レビューを通すためだけの無関係な掃除をしない。
- `APPROVED` を終了条件に置くが、停止判断は固定サイクル数ではなく、改善の有無、failure mode、人間判断の要否、review 単位の適切さで行う。
- レビュー入力には、変更箇所だけでなく依存先とデータフローの文脈を最低限含める。workflow-heavy な変更では `plan.md`、`tasks.md`、`implementation_gap_audit.md` を原則として含める。
- 中間ファイルは `.agents/context/codex_impl_review.md` に置き、`.agents/reviews/impl-review.md` は共有しやすい要約版として扱う。
- cycle 数は観測値であり、主ルールにしない。
- 各 cycle で新しい高重要度の欠陥が減っている、alignment が改善している、または recovery で unblock できている限りは継続してよい。
- 同種指摘が減らずに反復する、残件が人間の優先度判断待ちになる、review 対象が広すぎて分割したほうがよい場合は、要点をまとめて人間へ返す。
- runner が作る `.agents/context/_codex_input.tmp` をそのまま再利用し、別の補助スクリプトを増やさない。
- manual fallback では `Failure mode:` を固定ラベルで残し、`quality` と `recovery` を混同しない。
- 長い review が `recovery` や `alignment` cycle を多く含んだ場合は、repo に `handover-skills` があれば handover artifact を更新してから閉じる。
- `CONDITIONAL` / `REVISE` のたびに止まらず、自分で修正して再レビューまで進める。
