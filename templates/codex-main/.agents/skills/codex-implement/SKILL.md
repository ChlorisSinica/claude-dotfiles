---
name: codex-implement
description: "`.agents/context/tasks.md` の次の未完了タスクを、局所的な変更と逐次検証で実行する。計画が固まり、実装を小さく検証可能な単位で進めたいとき、plan / implementation drift や verify wrapper failure が起きる repo で mismatch audit と fallback verification を挟みながら進めたいとき、または runtime symptom を boundary-based triage と boundary contract review で潰しながら進めたいときに使う。"
---

# Codex Implement

計画済みの作業を、検証を密に保ちながら段階的に実装する。

## Workflow

1. `.agents/context/tasks.md` を読む。workflow-heavy な変更や既知の mismatch がある場合は `.agents/context/plan.md` と `.agents/context/implementation_gap_audit.md` も読む。
2. 次の未完了タスクを選ぶ。ただし plan / implementation drift、古い task wording、実装順の前提崩れを見つけた場合は、その audit を先に行ってよい。
3. 新しい mismatch を見つけた場合は、作業続行前に `.agents/context/implementation_gap_audit.md` を作成または更新して既知差分を明文化する。
4. そのタスクを満たす最小限で安全な変更を入れる。`.py` ファイルを Write/Edit した直後は `{{PYTHON_LAUNCHER}} -m py_compile <file>` で構文を通す。`IndentationError` / `SyntaxError` はパース段階で出るため try/except では捕捉できず、静的検証を素通りして runtime まで潜む。失敗したファイルは次のステップへ進む前に修正する。
5. 変更が helper return、worker/UI payload、file/sync artifact、startup/commit 境界に触れる場合は、実装前後に `boundary contract review` を行う。少なくとも `event payload schema`、`helper return type/materialization`、`file/sync artifact contract` のどれに当たるかを確認する。
6. タスク固有の検証があれば実行する。
7. 検証は `static verification`、`direct runtime probe`、`real-environment validation` を区別して扱う。どの層まで通ったか、どこが未実施かを task または audit に残す。
8. プロジェクト全体検証は repo 付属の verify runner を優先する。`{{PYTHON_LAUNCHER}} .claude/scripts/run-verify.py` を正規経路にする。
9. verify wrapper 自体が quoting / environment / compatibility の問題で壊れている場合は、その failure mode を `.agents/context/failure_report.md` に残し、`.agents/AGENTS.md` にある最小の直接検証へ切り替える。failure mode には `empty-output`、`permission-failure`、`compatibility-bug`、`broken-wrapper`、`unknown` の固定ラベルを優先する。wrapper failure だけでコード不良と断定しない。
10. runtime symptom が残る場合は、特定ログ名を最初の入口に固定せず `input -> launch -> render -> startup/init -> worker -> commit` の boundary 順で切り分ける。各 boundary では `caller-side log`、`callee-side log`、`user-visible UI`、`artifact on disk` から最低 1 つの observable を取る。
11. 検証が通ってからタスクを完了扱いにする。残るリスクがある場合は task または audit に明示する。
12. 意味のある実装単位がまとまったら `codex-impl-review` に回せるよう差分と文脈を整理する。workflow-heavy な変更では `plan.md`、`tasks.md`、`implementation_gap_audit.md` を review 入力に含める前提で整える。

## ルール

- 編集は局所的に保つ。
- 無関係なリファクタを避ける。
- インターフェースやデータフローを変えたら、上流と下流の影響を確認する。
- `構文が通る` と `実装が動く` を同一視しない。runtime 層の未確認を黙って完了扱いにしない。
- runtime 調査では `first log to check` を固定化しすぎず、boundary ごとに cheapest observable を選ぶ。
- runtime bug の多くは boundary contract の曖昧さから出る前提で、payload / helper return / artifact 契約を独立に見る。
- workflow や task の意味が変わったら、stale な task wording や obsolete な前提を残さない。
- 同じ失敗が繰り返される場合は `.agents/templates/failure_report.md` を `.agents/context/failure_report.md` にコピーして埋める。
- recovery や alignment を多く含む長いサイクルになった場合は、`handover-skills` があれば handover artifact を更新してから閉じる。
