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
- `templates/project-init/` — 開発プロジェクト初期化テンプレート
- `templates/research-survey/` — 研究サーベイ用テンプレート
- `scripts/init-project.sh` — テンプレート展開スクリプト（`/init-project` から呼び出し）
- `scripts/survey-convert.sh` — Markdown → LaTeX 変換スクリプト

## 更新

```bash
cd ~/claude-dotfiles
git pull
bash setup.sh       # 新規ファイルのみコピー
bash setup.sh -f    # 全ファイル上書き（既存を更新したい場合）
```

## codex-plugin-cc のインストール（推奨）

`/codex:review`（汎用レビュー）や `/codex:adversarial-review` を使う場合に推奨です。Claude Code のチャット内で以下を実行してください:

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

Codex CLI が未インストールの場合は `/codex:setup` が自動インストールを提案します。未ログインの場合は `! codex login` を実行してください。

## 使い方

任意のプロジェクトで Claude Code を起動し:

```
/init-project python-pytorch
```

### 開発プリセット

`python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`

### 研究サーベイプリセット

```
/init-project survey-cv
/init-project survey-ms
```

- `survey-cv` — Computer Vision（CVPR, ICCV, ECCV 等）
- `survey-ms` — Materials Science（Acta Materialia, Computational Materials Science 等）

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
