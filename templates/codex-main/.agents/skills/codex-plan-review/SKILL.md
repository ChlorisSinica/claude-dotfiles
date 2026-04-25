---
name: codex-plan-review
description: "`.agents/context/plan.md` と `.agents/context/tasks.md` を 2 段階でレビューし、設計前提と記述品質を分離して収束させる。workflow / state-machine / hotkey / lifecycle 変更を含む大きな plan で、固定サイクル数ではなく verdict・未解決論点・failure mode・implementation gap baseline に基づいて停止判断したいときに使う。"
---

# Codex Plan Review

plan.md と tasks.md の Codex クロスレビューを 2 段階で行い、設計判断と記述品質を分離して収束させる。

## Workflow

1. `.agents/context/plan.md` と `.agents/context/tasks.md` を読む。`snippets.md` があれば読む。workflow / hotkey / lifecycle / state-machine / control-flow の変更を含む plan か先に判定する。
2. Feature 名は次の優先順で決める。明示引数、`plan.md` の Objective、なければ短い要約。
3. review runner は Python で実行する。`Python 3.11+` の実行可能ランタイムを正規経路にする。
4. Phase A では `.agents/prompts/codex_plan_arch_review.md` を使い、設計判断だけをレビューする。
5. まず `{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-plan-review.py --phase arch` を使う。ad hoc な長い 1 行コマンドや一時 `_tmp` スクリプトは避ける。長時間 review で待ち時間を延ばしたい場合だけ `--review-timeout-sec <seconds>` を付ける。既定は 600 秒。
6. runner は prompt, plan.md, tasks.md, snippets.md を `.agents/context/_codex_input.tmp` に束ね、前回結果が `.agents/context/codex_plan_arch_review.md` にあれば同じ Phase 内だけ末尾へ注入する。
7. runner は `codex review -` を実行し、出力を `.agents/context/codex_plan_arch_review.md` と `.agents/reviews/plan-arch-review.md` に保存する。
8. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗、runner 互換不良で止まった場合は、`.agents/prompts/codex_plan_arch_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。`Failure mode:` は `permission-denied` / `empty-output` / `environment` / `runner-compat` / `unknown` の固定ラベルで残す。
9. 手動レビューでも Phase A の判定は `APPROVED` / `DISCUSS` / `REVISE` 相当で扱う。各記録には必要に応じて `Cycle type:` を `quality` / `alignment` / `recovery` / `decision` のいずれかで残す。
10. Phase A の `VERDICT:` を確認する。`APPROVED` 相当なら Phase B に進む。
11. Phase A で `REVISE` なら plan / tasks / snippets を修正して同じ Phase を即 rerun する。各 rerun は、重要な矛盾、未解決リスク、記述不足のいずれかを実質的に減らせるときだけ続ける。
12. Phase A で `DISCUSS` なら論点を要約して人間へ返す。勝手に設計変更しない。
13. Phase B では `.agents/prompts/codex_plan_review.md` を使い、記述品質と DoD をレビューする。
14. `{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-plan-review.py --phase detail` を使う。Phase B でも長時間 review だけ `--review-timeout-sec <seconds>` を追加してよい。
15. runner は prompt, plan.md, tasks.md, snippets.md を再結合し、前回結果が `.agents/context/codex_plan_tasks_review.md` にあれば同じ Phase 内だけ末尾へ注入する。
16. runner は `codex review -` を実行し、出力を `.agents/context/codex_plan_tasks_review.md` と `.agents/reviews/plan-review.md` に保存する。
17. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗、runner 互換不良で止まった場合は、`.agents/prompts/codex_plan_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。同じ固定ラベルで `Failure mode:` を残す。
18. 手動レビューでも Phase B の判定は `APPROVED` / `DISCUSS` / `REVISE` 相当で扱う。必要に応じて `Cycle type:` を残す。
19. Phase B の `VERDICT:` を確認する。`APPROVED` 相当なら必要に応じて `.agents/reviews/plan-review-summary.md` に要点を残す。
20. workflow-heavy な plan を扱った場合は、Phase B 完了時に `.agents/context/implementation_gap_audit.md` を作成または更新し、期待する trigger、control flow、state transition、後続 impl で監査すべき差分の baseline を残す。
21. Phase B で `REVISE` なら記述を修正して即 rerun する。`DISCUSS` なら論点を要約して人間へ返す。
22. runner は `.agents/reviews/sessions.json` に cycle 数を残すが、これは停止条件ではなく観測値として扱う。

## ルール

- Phase A では設計判断だけを扱い、詳細記述は持ち込まない。
- Phase B では設計の是非へ戻らない。ただし安全性や前提破綻に関わる矛盾を見つけた場合だけ Phase A 相当の論点として戻してよい。
- 前回指摘の注入は同じ Phase 内に限定する。
- `APPROVED` を取るために指摘を黙殺しないが、門番化もしない。
- 重大な未解決論点が外部情報依存なら Discussion Points に戻し、必要なときだけ Sonnet bridge を使う。
- 固定の最大サイクル数を主ルールにしない。cycle 数は観測値であり、停止判断は `VERDICT`、未解決論点、改善の有無、failure mode、人間判断の要否で行う。
- 各 cycle で新しい高重要度の欠陥が減っている、または plan / tasks の整合性が実質的に改善している限りは継続してよい。
- 同種の論点が減らずに反復する、残件が人間の優先度判断待ちになる、review 単位が大きすぎて分割すべきと判断した場合は、要点をまとめて人間へ返す。
- workflow-heavy な plan では implementation gap baseline を残してから閉じる。
- 長い review が `recovery` や `alignment` cycle を多く含んだ場合は、repo に `handover-skills` があれば handover artifact を更新してから閉じる。
- `REVISE` は自動で修正して rerun する。`DISCUSS` だけを人間判断に戻す。
