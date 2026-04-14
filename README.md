# Claude Code Dotfiles

Claude Code × Codex 連携ワークフローのグローバル設定。

## 早見表

- Claude Code 主体で使う: [Claude Workflow](./docs/claude-workflow.md)
- Codex 主体で使う: [Codex Workflow](./docs/codex-workflow.md)
- 研究サーベイ用: [Research Survey](./docs/research-survey.md)
- Windows Terminal 補助: [Windows Terminal](./docs/windows-terminal.md)
- ステータスライン: [Statusline](./docs/statusline.md)

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles
bash ~/claude-dotfiles/setup.sh
```

Codex 用の global skills も入れる場合:

```bash
bash ~/claude-dotfiles/setup.sh --codex
```

既存の Claude / Codex 用ファイルを上書き更新する場合:

```bash
bash ~/claude-dotfiles/setup.sh -f --codex
```

> **注意**: Windows では Git Bash を使用してください（コマンドプロンプトでは正常に動作しません）。

`~/.claude/` に以下がインストールされます:

- `commands/init-project.md` — `/init-project` グローバルコマンド
- `commands/update-workflow.md` — 既存プロジェクトの workflow files 更新コマンド
- `commands/update-skills.md` — `/update-workflow` の互換 alias
- `templates/project-init/` — 開発プロジェクト初期化テンプレート
- `templates/research-survey/` — 研究サーベイ用テンプレート
- `templates/codex-main/` — Codex-first プロジェクト用テンプレート
- `scripts/init-project.ps1` — テンプレート展開スクリプト本体（`/init-project` から呼び出し）
- `scripts/init-project.sh` — 互換ラッパ
- `scripts/survey-convert.sh` — Markdown → LaTeX 変換スクリプト

`setup.sh --codex` を使うと、さらに `~/.codex/skills/` に以下の global skills が入ります:

- `init-project-codex` — Codex から `codex-main` scaffold を作る入口
- `update-workflow-codex` — 既存の Codex-first workflow asset を更新する入口

初回導入は `setup.sh --codex` で十分です。`-f` は既存ファイルを上書き更新したいときだけ使用してください。

## グローバル設定の更新

```bash
cd ~/claude-dotfiles
git pull
bash setup.sh             # Claude 用の新規ファイルのみコピー
bash setup.sh -f          # Claude 用ファイルを上書き更新
bash setup.sh --codex     # Claude + Codex 用の新規ファイルのみコピー
bash setup.sh -f --codex  # Claude + Codex 用ファイルを上書き更新
```

## 使い方

入口は 3 種類あります。

- Claude Code: `/command`
- Codex: `$skill`
- PowerShell 直実行: `~/.claude/scripts/*.ps1`

PowerShell 直実行時の注意:

- `~/.claude/...` はホームディレクトリ配下を指す
- `/.claude/...` は Windows では `C:\.claude\...` 扱いになるため使わない
- 明示パスにしたい場合は `C:\Users\CVSLab\.claude\scripts\init-project.ps1` のように書く

### Claude Code

```
/init-project python-pytorch
```

既存プロジェクトで workflow files だけ更新:

```
/update-workflow python-pytorch
```

### Codex

```
$init-project-codex python
```

既存プロジェクトの Codex workflow asset を更新:

```
$update-workflow-codex python
```

### PowerShell 直実行

新規 Codex-first scaffold:

```powershell
~/.claude/scripts/init-project.ps1 --codex-main python
```

既存 Codex-first repo の workflow 更新:

```powershell
~/.claude/scripts/init-project.ps1 --codex-main python --workflow-only -f
```

PowerShell セッション内で `~/.claude/scripts/init-project.ps1 --codex-main <preset>` を実行すると、`.agents/` を主軸とした Codex-first scaffold を生成します。ランタイム設定だけは `.claude/settings.json` と `.claude/settings.local.json.bak` に出力されます。テンプレート定義自体は従来どおり `~/.claude/templates/` から配布されます。

`/init-project --codex-main <preset>` は Claude Code から同じ処理を呼ぶための互換入口です。

`/update-workflow` は `.claude/context/` と `.claude/agents/sessions.json` を保持しつつ、template-managed files と generated workflow files（`.claude/CLAUDE.md`、`.claude/settings.json`、`.claude/settings.local.json`、`.claude/hooks/syntax-check.py`、`.gitignore` を含む）を更新します。

生成される主な資産は `.agents/skills/`, `.agents/context/`, `.agents/reviews/`, `.claude/settings.json`, `.claude/settings.local.json.bak`, `scripts/run-verify.{sh,ps1}`, `scripts/run-codex-plan-review.ps1`, `scripts/run-codex-impl-review.ps1` です。

新しく展開された repo-local commands / skills は、起動中の Claude Code / Codex セッションには即時反映されないことがあります。使えない場合は一度セッションを開き直すか、アプリを再起動してください。

### Codex-first の最短フロー

初回セットアップ:

```bash
bash ~/claude-dotfiles/setup.sh --codex
```

新規プロジェクトを Codex-first で初期化:

```text
$init-project-codex ahk
```

この `$init-project-codex` は Codex 上の入口名で、実際の scaffold 本体は PowerShell から呼ぶ `~/.claude/scripts/init-project.ps1 --codex-main <preset>` です。

既存プロジェクトの `.agents` workflow asset を更新:

```text
$update-workflow-codex ahk
```

初期化後の主な入口:

- `.agents/skills/codex-research` — コードベース調査
- `.agents/skills/codex-plan` — plan/tasks 作成
- `.agents/skills/codex-plan-review` — plan/tasks の 2 段階レビュー
  中間結果は `.agents/context/codex_plan_*.md`、共有用結果は `.agents/reviews/` に保存
- `.agents/skills/codex-implement` — 実装と検証
- `.agents/skills/codex-impl-review` — 実装変更の APPROVED までの再レビュー
  `.agents/context/_codex_input.tmp` に入力を束ね、中間結果は `.agents/context/codex_impl_review.md` に保存
- `.agents/skills/codex-review` — 単発レビュー
- `.agents/skills/sonnet-dp-research-bridge` — 必要時のみ Claude / Sonnet へ人力委譲

Codex-first の基本フロー:

```text
$init-project-codex → $codex-research → $codex-plan
                    → $codex-plan-review
                    → $sonnet-dp-research-bridge（必要時のみ）
                    → $codex-implement → $codex-impl-review
```

補足:

- `$...` は Codex から呼ぶ skill / 入口名
- 実ファイル生成は `init-project.ps1` が担当
- `codex-main` の review 系は `.agents/skills/*` と `.agents/prompts/*` を使う運用で、Claude Code の `/...` コマンドとは別系統

## codex-plugin-cc のインストール（Claude Code から `/codex:*` を使う場合に推奨）

`/codex:review`（汎用レビュー）や `/codex:adversarial-review` を使う場合に推奨です。Claude Code のチャット内で以下を実行してください:

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

Codex CLI が未インストールの場合は `/codex:setup` が自動インストールを提案します。未ログインの場合は `! codex login` を実行してください。

## ワークフロー

### Claude Code の開発ワークフロー

```
/init-project → /research → /plan → /sonnet-dp-research（省略可
              → /codex-plan-review → /implement → /codex-impl-review
              → /handover, retro
```

**前提**: Codex CLI (`npm install -g @openai/codex`) が必要です。codex-plugin-cc は `/codex:review`（汎用レビュー）を使う場合に推奨です。

### 研究サーベイワークフロー

```
/init-project survey-cv → /scope <topic>
                        → /search → /read → /outline
                        → /draft → /review → /convert
```

**前提**: `/convert` には Pandoc が必要です（`winget install --id JohnMacFarlane.Pandoc`）。

## 開発プリセット

- 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`
- 研究用: `survey-cv`, `survey-ms`

## 詳細ドキュメント

- [Claude Workflow](./docs/claude-workflow.md)
- [Codex Workflow](./docs/codex-workflow.md)
- [Research Survey](./docs/research-survey.md)
- [Windows Terminal](./docs/windows-terminal.md)
- [Statusline](./docs/statusline.md)
