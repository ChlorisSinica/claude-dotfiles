---
name: handover-skills
description: "長い実装 / review サイクルの終了時に、今回使った workflow skills の問題点、runner failure、manual fallback、未解決リスク、次担当者向けの引き継ぎ手順を整理する。`codex-plan` / `codex-plan-review` / `codex-implement` / `codex-impl-review` などの repo-local skill を使ったあと、次の担当者が同じ詰まり方をしないよう handover 文書を残したいときに使う。"
---

# Handover Skills

長いサイクルの終了時に、skill 運用上の問題点と次担当者向けの再開手順を、短く再利用可能な形へ固める。

## Workflow

1. 今回使った skill を列挙する。対象は会話ログ、review 記録、`plan.md` / `tasks.md` / review artifacts から実際に使ったものだけに限定する。
2. 各 skill について、今回の cycle で観測された問題を「skill 本文の不足」と「repo / runner / wrapper の故障」に分けて整理する。
3. 問題点は `.agents/context/skill_handover_issues.md` に保存する。
4. 次担当者向けの再開手順は `.agents/context/handover_skills_procedure.md` に保存する。
5. handover には少なくとも次を含める。
   - 今回使った skill 名
   - 各 skill の observed problem
   - impact
   - suggested fix
   - 既知の壊れた runner / wrapper
   - 次担当者が最初に読むべきファイル
   - 最小の再検証コマンド
6. 既存の review 記録がある場合は、cycle 数や verdict を壊さずに追記・更新する。過去の判断を黙って書き換えない。

## Output Rules

- `skill_handover_issues.md` は skill ごとに section を分け、`Observed problem` / `Impact` / `Suggested fix` を明示する。
- `handover_skills_procedure.md` は番号付き手順で書く。
- 問題点は今回の artifacts から確認できたものだけを書く。推測を書く場合は推測だと明示する。
- 同じ問題を skill 側と repo 側の両方に重複計上しない。主因を分けて書く。

## Rules

- 単なる一般論ではなく、この repo の workflow で実際に詰まった点を優先する。
- runner が空返りした場合は、空返り自体と、その結果どの manual fallback が必要だったかをセットで残す。
- `plan` と `implementation` のずれを後追いで直した場合は、どの skill がそのずれを早期検出できなかったかも残す。
- 未解決の runtime risk が残る場合は、次担当者が最初に行う実機確認や最小再検証を procedure に入れる。
