# Claude Code Dotfiles

Claude Code × Codex 連携ワークフローのグローバル設定。

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles
bash ~/claude-dotfiles/setup.sh
```

> **注意**: Windows では Git Bash を使用してください（コマンドプロンプトでは正常に動作しません）。

`~/.claude/` に以下がインストールされます:

- `commands/init-project.md` — `/init-project` グローバルコマンド
- `commands/update-workflow.md` — 既存プロジェクトの workflow files 更新コマンド
- `commands/update-skills.md` — `/update-workflow` の互換 alias
- `templates/project-init/` — 開発プロジェクト初期化テンプレート
- `templates/research-survey/` — 研究サーベイ用テンプレート
- `scripts/init-project.sh` — テンプレート展開スクリプト（`/init-project` から呼び出し）
- `scripts/survey-convert.sh` — Markdown → LaTeX 変換スクリプト

## グローバル設定の更新

```bash
cd ~/claude-dotfiles
git pull
bash setup.sh       # 新規ファイルのみコピー
bash setup.sh -f    # 全ファイル上書き（既存を更新したい場合）
```

## 使い方

通常は Claude Code コマンドを入口にしてください。

新規プロジェクト:

```
/init-project python-pytorch
```

既存プロジェクトで workflow files だけ更新:

```
/update-workflow python-pytorch
```

`/update-skills` は互換 alias として残っていますが、今後は `/update-workflow` を優先してください。

### 開発プリセット

`python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`

### 研究サーベイプリセット

```
/init-project survey-cv
/init-project survey-ms
/update-workflow survey-cv
/update-workflow survey-ms
```

- `survey-cv` — Computer Vision（CVPR, ICCV, ECCV 等）
- `survey-ms` — Materials Science（Acta Materialia, Computational Materials Science 等）

## 手動 Fallback

Claude Code コマンドを使わずに手動で workflow files を更新したい場合:

```bash
bash ~/.claude/scripts/init-project.sh -t <template> <preset> --workflow-only -f
```

例:

```bash
bash ~/.claude/scripts/init-project.sh -t project-init python-pytorch --workflow-only -f
bash ~/.claude/scripts/init-project.sh -t research-survey survey-cv --workflow-only -f
```

`--workflow-only -f` は `.claude/commands/` と `.claude/agents/` を上書き更新し、`.claude/context/`、`CLAUDE.md`、`settings.json`、`settings.local.json`、`.gitignore`、`agents/sessions.json` は保持します。`--skills-only` は後方互換 alias です。

## codex-plugin-cc のインストール（推奨）

`/codex:review`（汎用レビュー）や `/codex:adversarial-review` を使う場合に推奨です。Claude Code のチャット内で以下を実行してください:

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

Codex CLI が未インストールの場合は `/codex:setup` が自動インストールを提案します。未ログインの場合は `! codex login` を実行してください。

## ステータスライン

[nyosegawa.com Pattern5](https://nyosegawa.com/posts/claude-code-statusline-rate-limits/) を拡張した2行構成のカスタムステータスライン:

```
Opus 4.6 (1M context)
ctx ⣄        5% (50k/1.0M) │ 5h ⣤        6% (2h55m) │ 7d ⣿⣿⣿⣤     44% (1d6h)
```

- **1行目**: モデル名
- **2行目**: コンテキスト使用量 (トークン数) / 5時間レート制限 (残り時間) / 7日レート制限 (残り時間)
- Braille ドットバーにグラデーション着色 (緑→黄→赤)

### セットアップ

```bash
bash ~/claude-dotfiles/setup.sh --statusline      # setup.sh と同時にインストール
bash ~/claude-dotfiles/setup-statusline.sh        # ステータスラインのみ
bash ~/claude-dotfiles/setup-statusline.sh -f     # 上書き更新
```

## ワークフロー

### 開発ワークフロー

```
/init-project → /research
             → /plan → /sonnet-dp-research（省略可）→ /codex-plan-review
             → /implement → /codex-impl-review
```

**前提**: Codex CLI (`npm install -g @openai/codex`) が必要です。codex-plugin-cc は `/codex:review`（汎用レビュー）を使う場合に推奨です。

### 研究サーベイワークフロー

```
/init-project survey-cv → /scope <topic>
                        → /search → /read → /outline
                        → /draft → /review → /convert
```

**前提**: `/convert` には Pandoc が必要です（`winget install --id JohnMacFarlane.Pandoc`）。

## 自動承認（Auto-Approve）

ワークフローの自律ループ中にツール承認が大量発生するのを防ぐため、`settings.local.json`（git-ignored）で自動承認を設定できます。

`/init-project` 実行時に `settings.local.json.bak` として生成されます（**デフォルト OFF**）。

### 自動承認の ON/OFF 切り替え

対象プロジェクトのルートディレクトリで実行:

```bash
cd /path/to/your/project

# ON — 自動承認を有効化（初回）
mv .claude/settings.local.json.bak .claude/settings.local.json

# OFF — 全ツールを毎回手動承認に戻す
mv .claude/settings.local.json .claude/settings.local.json.bak
```

### 開発ワークフローで承認が必要なツール

| コマンド | ツール | 発生回数 |
|---------|--------|---------|
| `/codex-plan-review` | `Bash(cat ... \| codex review -)` | Phase A 最大2回 + Phase B 最大3回 |
| `/codex-impl-review` | `Bash(cat ... \| codex review -)` | 最大5サイクル |
| `/sonnet-dp-research` | `WebSearch`, `WebFetch` | Discussion Point 数×複数回 |
| `/implement` | `Bash({{VERIFY_CMD}})`, `Edit`, `Write` | タスク数×毎回 |
| `/implement` (完了後) | `Bash(git add/commit)` | 1回 |

自動承認を有効にする場合、`settings.local.json` に以下を追加:

```json
{
  "permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(codex review:*)",
      "Bash(cat .claude/context/*)",
      "Bash(powershell:*)",
      "WebSearch",
      "WebFetch"
    ]
  }
}
```

> **注意**:
> - `Bash(git *)` や `Bash(*)` は `git push` も自動承認されるため使用しないこと
> - `git push` は手動承認を維持する
> - 上記は共通部分のみ。検証コマンド（`python -m pytest`, `cargo test` 等）のパターンは `/init-project` 時に `settings.local.json.bak` へ自動生成される

### 研究サーベイワークフローで承認が必要なツール

| コマンド | ツール | 発生回数 |
|---------|--------|---------|
| `/search` | `WebSearch` | 検索クエリ数×複数回 |
| `/read` | `WebFetch`, `Bash(pqa/paper/marker_single)` | 論文数×毎回 |
| `/review` | `Bash(python -c ... semanticscholar)`, `WebSearch` | 引用数×毎回 |
| `/convert` | `Bash(pandoc/bibcure)` | 1回 |

研究テンプレートでは `/init-project` 時に `settings.local.json.bak` として生成されます（デフォルト OFF）。ON にすると以下が自動承認されます:

- `WebSearch` — 全検索クエリ
- `WebFetch` — arxiv.org, semanticscholar.org, scholar.google.com, openreview.net, aclanthology.org, papers.nips.cc, openaccess.thecvf.com, doi.org
- `Bash` — git, pqa, paper, marker_single, bibcure, pandoc, python -c
