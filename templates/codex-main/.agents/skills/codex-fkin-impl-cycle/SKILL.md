---
name: codex-fkin-impl-cycle
description: "`.agents/context/tasks.md` の次の task または milestone を実装し、Python ベースの review cycle で `alignment -> verification -> quality` を収束させる。pwsh 依存を避けつつ、`--dry-run`、`--dump-bundle`、`--write-trace` 付きで実装・自己レビュー・デバッグを進めたいときに使う。"
---

# Codex Fkin Impl Cycle

task-slice 実装と phase-aware review を、Python runner を正規経路として進める。

## Workflow

1. `.agents/context/tasks.md` を読む。必要なら `.agents/context/plan.md` と `.agents/context/implementation_gap_audit.md` も読む。
2. 次の未完了 task を選ぶ。task 単独で意味を持たない変更だけ milestone 単位に広げてよい。
3. task を満たす最小限で安全な変更を入れる。
4. review 対象ファイルと依存ファイルを決める。
5. `alignment` review を実行する。
6. drift を修正したら `verification` review を実行する。
7. 必須 verification を揃えたら `quality` review を実行する。
8. broad quality で見つかった修正は、影響範囲に応じて `alignment`、`verification`、または実装へ戻す。
9. phase ごとの high-severity 指摘が収束したら次の task へ進む。

## Scope And Exit

- 各 phase は `今回の task / milestone / task-description で宣言した current slice` を主対象にする。
- `verification` はまず fresh scaffold、declared dogfood scope、generated runner の直接動作確認を優先する。
- `existing install の完全収束` や `旧 repo 全体の完全 cleanup` は、明示 task に入っていない限り default では追い込まない。
- `current slice` の correctness が通っていて、残りが migration completeness や cleanup completeness だけなら、follow-up task に落として `APPROVED` 相当で次 phase または次 task へ進んでよい。
- 同種の migration hygiene 指摘が 2 回続いたら、cycle を回し続けるより task 化と residual risk 明示を優先する。

## Runner

通常は次の Python runner を使う。

- 通常の repo: `{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-impl-cycle.py`
- dotfiles repo 直作業: `{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-impl-cycle.py`

Linux で `python` が無い環境では `python3` に読み替えてよい。

### Recommended Commands

```text
{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-impl-cycle.py --cycle-type alignment --files <files...> --include-files <deps...>
{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-impl-cycle.py --cycle-type verification --files <files...> --include-files <deps...>
{{PYTHON_LAUNCHER}} .agents/scripts/run-codex-impl-cycle.py --cycle-type quality --files <files...> --include-files <deps...>
```

## Debug / Validation

- 新しい repo や prompt 構成で最初に使うときは、先に `--dry-run` を実行して bundle を確認する。
- prompt や前回 review 注入を確認したいときは `--dump-bundle <path>` を使う。
- path 解決や phase artifact の追跡には `--debug` を使う。
- 実行メタ情報を残したいときは `--write-trace <path>` を使う。
- runner failure と code failure を混同しない。verification phase では `static`、`runtime probe`、`real-environment` を分けて扱う。

## Rules

- `Phase B -> alignment`
- `Phase C -> verification`
- `Phase D -> quality`
- review は原則 `1 task` ごとに回し、広域 quality は `task batch` または `全 task 完了後` に強めに見る。
- `approve 数` ではなく `spec drift`、`verification gap`、`severity` で gate する。
- broad review の修正後は毎回実装フェーズへ戻さず、実際の影響範囲に合わせて戻り先を決める。
- 既存 `.ps1` runner は legacy/fallback として扱い、新 cycle の正規経路にはしない。
- migration hygiene の完全性は、current slice の correctness を直接壊す場合だけ高優先度で扱う。
- review が current slice を越えて legacy cleanup を掘り続ける段階に入ったら、skill 利用者は rerun より stop judgement を優先してよい。
