---
name: codex-plan-review
description: "`.agents/context/plan.md` と `.agents/context/tasks.md` を、Codex review の 2 段階サイクルでレビューする。設計前提の検証と詳細品質の確認を分け、APPROVED まで繰り返したいときに使う。"
---

# Codex Plan Review

plan.md と tasks.md の Codex クロスレビューを 2 段階で行う。

## Workflow

1. `.agents/context/plan.md` と `.agents/context/tasks.md` を読む。`snippets.md` があればそれも読む。
2. Feature 名は次の優先順で決める。明示引数、`plan.md` の Objective、なければ短い要約。
3. review runner は `pwsh` で実行する。Windows PowerShell 5.1 ではなく `pwsh -NoProfile -ExecutionPolicy Bypass -File ...` を正規経路にする。
4. Phase A では `.agents/prompts/codex_plan_arch_review.md` を使い、設計判断だけをレビューする。
5. まず `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-codex-plan-review.ps1 -Phase arch` を使う。ad hoc な長い 1 行コマンドや一時 `_tmp` スクリプトは避ける。
6. runner は prompt, plan.md, tasks.md, snippets.md を `.agents/context/_codex_input.tmp` に束ね、前回結果が `.agents/context/codex_plan_arch_review.md` にあれば末尾へ注入する。
7. runner は `codex review -` を実行し、出力を `.agents/context/codex_plan_arch_review.md` と `.agents/reviews/plan-arch-review.md` に保存する。
8. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗で止まった場合は、`.agents/prompts/codex_plan_arch_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。
9. 手動レビューでも Phase A の判定は `APPROVED` / `DISCUSS` / `REVISE` 相当で扱い、結果と修正内容を `.agents/context/codex_plan_arch_review.md` または `.agents/reviews/plan-arch-review.md` に残す。
10. Phase A の `VERDICT:` と `Cycle:` を確認する。`VERDICT: APPROVED` 相当なら Phase B に進む。
11. Phase A で `REVISE` なら plan / tasks / snippets を修正して、同じフェーズを即 rerun する。
12. Phase A で `DISCUSS` なら論点を要約して人間へ返す。勝手に設計変更しない。
13. Phase B では `.agents/prompts/codex_plan_review.md` を使い、記述品質と DoD をレビューする。
14. `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-codex-plan-review.ps1 -Phase detail` を使う。
15. runner は prompt, plan.md, tasks.md, snippets.md を再結合し、前回結果が `.agents/context/codex_plan_tasks_review.md` にあれば末尾へ注入する。
16. runner は `codex review -` を実行し、出力を `.agents/context/codex_plan_tasks_review.md` と `.agents/reviews/plan-review.md` に保存する。
17. runner が `codex review -` 実行時の権限エラー、空返り、環境依存失敗で止まった場合は、`.agents/prompts/codex_plan_review.md` を直接読み、その観点に沿った手動レビューへ切り替える。
18. 手動レビューでも Phase B の判定は `APPROVED` / `DISCUSS` / `REVISE` 相当で扱い、結果と修正内容を `.agents/context/codex_plan_tasks_review.md` または `.agents/reviews/plan-review.md` に残す。
19. Phase B の `VERDICT:` と `Cycle:` を確認する。`APPROVED` 相当なら必要に応じて `.agents/reviews/plan-review-summary.md` に要点を残す。
20. Phase B で `REVISE` なら記述を修正して即 rerun する。`DISCUSS` なら論点を要約して人間へ返す。
21. runner は `.agents/reviews/sessions.json` に cycle 数を残すので、判断時はそこも参照してよい。

## ルール

- Phase A では設計判断だけを扱い、詳細記述は持ち込まない。
- Phase B では設計の是非へ戻らない。
- 前回指摘の注入は同じフェーズ内に限定する。
- `APPROVED` を取るために指摘を黙殺しないが、門番化もしない。
- 重大な未解決論点が外部情報依存なら Discussion Points に戻し、必要なときだけ Sonnet bridge を使う。
- Phase A は最大 2 サイクル、Phase B は最大 3 サイクルを目安にし、超える場合は要点をまとめて人間へ返す。
- `REVISE` は自動で修正して rerun する。`DISCUSS` だけを人間判断に戻す。
