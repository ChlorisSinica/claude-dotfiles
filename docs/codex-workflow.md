# Codex Workflow

Codex 主体でこの dotfiles を使うときの入口です。`codex-main` は `.agents/` を主軸にしつつ、Codex ランタイム設定だけ `.claude/settings*.json` を使います。

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

PowerShell から直接呼ぶ場合:

```powershell
~/.claude/scripts/init-project.ps1 --codex-main ahk
~/.claude/scripts/init-project.ps1 --codex-main ahk --workflow-only -f
```

注意:

- `~/.claude/...` はホームディレクトリ配下を指す
- `/.claude/...` は Windows では `C:\.claude\...` 扱いになるため使わない
- 明示パスにしたい場合は `C:\Users\CVSLab\.claude\scripts\init-project.ps1`

## 開発ワークフロー

Codex-first で進めるときの基本フロー:

```text
$init-project-codex → $codex-research → $codex-plan
                    → $codex-plan-review
                    → $sonnet-dp-research-bridge（必要時のみ）
                    → $codex-implement → $codex-impl-review
```

役割:

- `$codex-research` はコードベース理解を `.agents/context/research.md` に残す
- `$codex-plan` は設計とタスクリストを `.agents/context/plan.md`, `.agents/context/tasks.md` に残す
- `$codex-plan-review` は plan/tasks を 2 段階でレビューし、中間結果を `.agents/context/codex_plan_*.md`、共有用結果を `.agents/reviews/` に残す
- `$codex-implement` は task 単位で実装し、`scripts/run-verify.*` で検証する
- `$codex-impl-review` は実装変更を APPROVED まで再レビューし、中間結果を `.agents/context/codex_impl_review.md`、共有用結果を `.agents/reviews/impl-review.md` に残す
- `$codex-review` は単発の ad-hoc review 用に残す
- `$sonnet-dp-research-bridge` は外部調査が必要な論点だけ Claude / Sonnet に人力委譲する

補足:

- 既存 repo の更新から始めるときは `$init-project-codex` の代わりに `$update-workflow-codex`
- 小さな修正では `$codex-research` や `$codex-review` を軽量化してよい

## 生成される主な資産

- `.agents/AGENTS.md`
- `.agents/skills/`
- `.agents/context/`
- `.agents/context/_codex_input.tmp`
- `.agents/reviews/`
- `.agents/prompts/`
- `.agents/templates/`
- `.claude/settings.json`
- `.claude/settings.local.json.bak`
- `scripts/run-verify.sh`
- `scripts/run-verify.ps1`
- `scripts/run-codex-plan-review.ps1`
- `scripts/run-codex-impl-review.ps1`

## 反映タイミング

- 新しく展開された repo-local skills は、起動中の Codex / Claude セッションには即時反映されないことがある
- 使えない場合は一度セッションを開き直すか、アプリを再起動する

## repo-local skill

- `.agents/skills/codex-research`
- `.agents/skills/codex-plan`
- `.agents/skills/codex-plan-review`
- `.agents/skills/codex-implement`
- `.agents/skills/codex-impl-review`
- `.agents/skills/codex-review`
- `.agents/skills/sonnet-dp-research-bridge`

## Sonnet 連携

`codex-main` は `.claude/commands` や `.claude/context` を自動展開しません。例外として、権限承認を減らすためのランタイム設定ファイル `.claude/settings.json` と `.claude/settings.local.json.bak` は生成されます。Claude / Sonnet 連携が必要なときだけ `.agents/skills/sonnet-dp-research-bridge` を使って人力で調査を委譲します。

## 関連ページ

- [Claude Workflow](./claude-workflow.md)
- [Research Survey](./research-survey.md)
