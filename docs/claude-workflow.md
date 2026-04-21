# Claude Workflow

Claude Code 主体でこの dotfiles を使うときの入口と運用メモです．

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles
python ~/claude-dotfiles/scripts/setup.py
```

更新時:

```bash
cd ~/claude-dotfiles
git pull
python scripts/setup.py
python scripts/setup.py -f
```

`python` は例です．環境に応じて `python3` や `py -3` など，Python 3.11+ の launcher に置き換えてください．

## 主な入口

新規プロジェクト:

```text
/init-project python-pytorch
```

既存プロジェクトの workflow 更新:

```text
/update-workflow python-pytorch
```

互換 alias:

```text
/update-skills python-pytorch
```

## `/init-project`

- 既定テンプレートは `project-init`
- `survey-cv`, `survey-ms` は `research-survey` テンプレートを使用
- `--codex-main` を付けると Codex-first テンプレートを Claude Code から互換的に呼べる

例:

```text
/init-project python
/init-project survey-cv
/init-project --codex-main python
```

生成直後の注意:

- 新しく展開された `.claude/commands/` や `.agents/skills/` は，起動中の Claude Code / Codex セッションには即時反映されないことがある
- 使えない場合は一度セッションを開き直すか，アプリを再起動する

## `/update-workflow`

- `.claude/context/` と runtime state を保持しつつ，template-managed files を更新
- `--codex-main` では `.agents/context/` と `.agents/reviews/` を保持しつつ Codex-first asset を更新

例:

```text
/update-workflow python
/update-workflow --codex-main python
```

## 開発ワークフロー

Claude Code 主体で進めるときの基本フロー:

```text
/init-project → /research → /plan → /sonnet-dp-research（省略可）
              → /codex-plan-review → /implement → /codex-impl-review
              → /handover, /retro
```

補足:

- `/sonnet-dp-research` は Discussion Point が残ったときだけ挟む
- `/codex-plan-review` と `/codex-impl-review` には Codex CLI が必要
- 小さな変更では `/research` や `/handover`, `/retro` を省略してよい

前提:

- Codex CLI: `npm install -g @openai/codex`
- `codex-plugin-cc` は `/codex:review` などの汎用レビューを使う場合に推奨

## Claude 側の自動承認

この節は `.claude/settings.local.json` を使う workflow 向けです．

`/init-project` 実行時に `.claude/settings.local.json.bak` が生成されます．必要なときだけ有効化してください．

```bash
cd /path/to/your/project

# ON
mv .claude/settings.local.json.bak .claude/settings.local.json

# OFF
mv .claude/settings.local.json .claude/settings.local.json.bak
```

注意:

- `Bash(git *)` や `Bash(*)` のような広い許可は避ける
- `git push` は手動承認のまま維持する
- 検証コマンドの許可候補は preset に応じて自動生成される

## Claude から Codex を使う場合

`codex-plugin-cc` は Claude Code から `/codex:*` を使う場合に便利です．

```text
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

## 関連ページ

- [Codex Workflow](./codex-workflow.md)
- [Research Survey](./research-survey.md)
- [Windows Terminal](./windows-terminal.md)
- [Statusline](./statusline.md)
