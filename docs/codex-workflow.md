# Codex Workflow

Codex 主体でこの dotfiles を使うときの入口です。`codex-main` は `.agents/` を主軸にしつつ、Codex ランタイム設定だけ `.claude/settings*.json` を使います。

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles
python ~/claude-dotfiles/scripts/setup.py --codex
```

更新時:

```bash
cd ~/claude-dotfiles
git pull
python scripts/setup.py --codex
python scripts/setup.py -f --codex
```

`setup.py --codex` は Claude 用資産に加えて `~/.codex/skills/` へ global skill も配布します。`python` は例なので、環境に応じて `python3` や `py -3` など Python 3.11+ launcher に置き換えてください。

## グローバル skill

- `init-project-codex` — Codex-first scaffold の作成
- `update-workflow-codex` — 既存 `.agents` workflow asset の更新

## 仕様整理

`codex-main` は次の 3 層で構成します。

- global 入口
  - `$init-project-codex`
  - `$update-workflow-codex`
  - 必要なら Claude Code から `/init-project --codex-main ...`
- Python 本体
  - `codex-main` の正規実装は `~/.claude/scripts/init-project.py`
  - 新規作成は `--codex-main <preset>`
  - 既存 repo 更新は `--codex-main <preset> --workflow-only -f`
- repo-local workflow
  - 調査、計画、実装は `.agents/skills/*` と `.agents/prompts/*`
  - review / verify の機械処理だけ `scripts/run-codex-*.py` と `scripts/run-verify.py`

要するに、`$...` は入口、`.py` は scaffold / update 本体、日々の開発フローは repo-local の `.agents/` で回す構成です。

## 最短フロー

新規プロジェクト:

```text
$init-project-codex ahk
```

既存プロジェクトの更新:

```text
$update-workflow-codex ahk
```

Python から直接呼ぶ場合:

```text
<python-launcher> ~/.claude/scripts/init-project.py --codex-main ahk
<python-launcher> ~/.claude/scripts/init-project.py --codex-main ahk --workflow-only -f
```

注意:

- `~/.claude/...` はホームディレクトリ配下を指す
- `/.claude/...` は Windows では `C:\.claude\...` 扱いになるため使わない
- 明示パスにしたい場合は `C:\Users\CVSLab\.claude\scripts\init-project.py`

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
- `$codex-plan-review` は plan/tasks を設計判断と記述品質に分けて収束レビューし、中間結果を `.agents/context/codex_plan_*.md`、共有用結果を `.agents/reviews/` に残す
- `$codex-implement` は task 単位で実装し、drift audit、verify wrapper fallback、runtime の boundary-based triage を入れつつ `scripts/run-verify.py` で検証する
- `$codex-impl-review` は実装変更を品質・整合性・recovery を切り分けながら収束レビューし、中間結果を `.agents/context/codex_impl_review.md`、共有用結果を `.agents/reviews/impl-review.md` に残す
- `$handover-skills` は長い cycle の skill 問題点と再開手順を handover artifact に残す
- review runner の正規実行経路は `<python-launcher> scripts/run-codex-*.py ...`
- review runner の既定 model / reasoning effort は `gpt-5.4 / high`
- `xhigh` は architecture の難所や 1 回限りの深掘りだけに使い、通常 rerun の既定にはしない
- `gpt-5.4-mini` は軽量 rerun 専用で、architecture gate や final gate の既定にはしない
- review runner の `codex review` 実行には既定で 600 秒の timeout がある。大きい review や一時的な backend 遅延で延ばしたい場合だけ `--review-timeout-sec <seconds>` を追加する
- review runner は 1 実行 = 1 cycle の bundle 作成、`codex review -` 実行、結果保存だけを担う
- `$codex-review` は単発の ad-hoc review 用に残す
- `$sonnet-dp-research-bridge` は外部調査が必要な論点だけ Claude / Sonnet に人力委譲する
- review runner は `.agents/reviews/sessions.json` に cycle 数の観測値と APPROVED 記録を残す

補足:

- 既存 repo の更新から始めるときは `$init-project-codex` の代わりに `$update-workflow-codex`
- 小さな修正では `$codex-research` や `$codex-review` を軽量化してよい

## 責務分担

- `setup / init / update` は Python runner を正規実装にする
- `research / plan / implement` は repo-local の `skills + prompts` を主役にする
- review は `skills + prompts` と `scripts/run-codex-*.py` の二層で扱う
- `skills + prompts` は review 観点、停止条件、どのフェーズへ進むかを定義する
- review runner は bundle 組み立て、`codex review -` 実行、結果保存のような機械的処理だけを担う
- 実装都合で runner を足しても、workflow の判断ロジック本体は `skills` 側に残す

## 生成される主な資産

- `.agents/AGENTS.md`
- `.agents/skills/`
- `.agents/context/`
- `.agents/context/_codex_input.tmp`
- `.agents/reviews/`
- `.agents/reviews/sessions.json`
- `.agents/prompts/`
- `.agents/templates/`
- `.claude/settings.json`
- `.claude/settings.local.json.bak`
- `scripts/run-verify.py`
- `scripts/run-codex-plan-review.py`
- `scripts/run-codex-impl-review.py`
- `scripts/run-codex-impl-cycle.py`

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

## Troubleshooting

- plugin manifest の warning `ignoring interface.defaultPrompt: prompt must be at most 128 characters` は、最新の Python review runner と `scripts/setup.py --codex` が `fix_codex_plugin_prompts.py` を best-effort 実行して抑制する
- `CreateProcessAsUserW failed: 5` / `windows sandbox: runner error` が出る場合、最新の review runner は `windows.sandbox="unelevated"` で自動再試行する。古い project runner では fallback がないため、`/update-workflow --codex-main <preset>` または `<python-launcher> ~/.claude/scripts/init-project.py --codex-main <preset> --workflow-only -f` で runner を更新する
- review 本文の `VERDICT:` は最後の非空行だけを有効扱いにする。warning や補足文で末尾が汚れた場合は fallback verdict を補って保存する
- `plugins/* 403 Forbidden` や shell snapshot warning は本文に混ぜないように分離するが、Codex 本体側の warning なので実行時間そのものは短縮しない。小規模 review で 10 分を超える場合は warning より backend 側または sandbox 初回失敗の影響を疑う

## 関連ページ

- [Claude Workflow](./claude-workflow.md)
- [Research Survey](./research-survey.md)
