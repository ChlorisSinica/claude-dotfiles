# Codex Workflow

Codex 主体でこの dotfiles を使うときの入口です。`codex-main` は `.claude/` ではなく `.agents/` を主軸にします。

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles
bash ~/claude-dotfiles/setup.sh --codex
```

更新時:

```bash
cd ~/claude-dotfiles
git pull
bash setup.sh --codex
bash setup.sh -f --codex
```

`setup.sh --codex` は Claude 用資産に加えて `~/.codex/skills/` へ global skill も配布します。

## グローバル skill

- `init-project-codex` — Codex-first scaffold の作成
- `update-workflow-codex` — 既存 `.agents` workflow asset の更新

## 最短フロー

新規プロジェクト:

```text
$init-project-codex ahk
```

既存プロジェクトの更新:

```text
$update-workflow-codex ahk
```

## 開発ワークフロー

Codex-first で進めるときの基本フロー:

```text
$init-project-codex → $codex-research → $codex-plan
                    → $sonnet-dp-research-bridge（必要時のみ）
                    → $codex-implement → $codex-review
```

役割:

- `$codex-research` はコードベース理解を `.agents/context/research.md` に残す
- `$codex-plan` は設計とタスクリストを `.agents/context/plan.md`, `.agents/context/tasks.md` に残す
- `$codex-implement` は task 単位で実装し、`scripts/run-verify.*` で検証する
- `$codex-review` は plan / 実装レビュー結果を `.agents/reviews/` に保存する
- `$sonnet-dp-research-bridge` は外部調査が必要な論点だけ Claude / Sonnet に人力委譲する

補足:

- 既存 repo の更新から始めるときは `$init-project-codex` の代わりに `$update-workflow-codex`
- 小さな修正では `$codex-research` や `$codex-review` を軽量化してよい

## 生成される主な資産

- `.agents/AGENTS.md`
- `.agents/skills/`
- `.agents/context/`
- `.agents/reviews/`
- `.agents/prompts/`
- `.agents/templates/`
- `scripts/run-verify.sh`
- `scripts/run-verify.ps1`

## repo-local skill

- `.agents/skills/codex-research`
- `.agents/skills/codex-plan`
- `.agents/skills/codex-implement`
- `.agents/skills/codex-review`
- `.agents/skills/sonnet-dp-research-bridge`

## 低レベル実装コマンド

global skill を使わず直接呼ぶ場合:

```bash
bash ~/.claude/scripts/init-project.sh --codex-main python
bash ~/.claude/scripts/init-project.sh --codex-main python --workflow-only -f
```

## Sonnet 連携

`codex-main` は `.claude` をプロジェクトへ自動展開しません。必要なときだけ `.agents/skills/sonnet-dp-research-bridge` を使って、人力で Claude / Sonnet へ調査を委譲します。

## 関連ページ

- [Claude Workflow](./claude-workflow.md)
- [Research Survey](./research-survey.md)
