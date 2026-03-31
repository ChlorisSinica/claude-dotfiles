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
- `templates/project-init/` — プロジェクト初期化テンプレート
- `statusline.py` — 2行カスタムステータスライン (Pattern 6)
- `settings.json` に `statusLine` 設定を自動追加

## 更新

```bash
cd ~/claude-dotfiles
git pull
bash setup.sh       # 新規ファイルのみコピー
bash setup.sh -f    # 全ファイル上書き（既存を更新したい場合）
```

## 使い方

任意のプロジェクトで Claude Code を起動し:

```
/init-project python-pytorch
```

プリセット: `python`, `python-pytorch`, `typescript`, `rust`, `autohotkey-v1`, `autohotkey-v2`

## ステータスライン

2行構成のカスタムステータスライン (Pattern 6):

```
Opus 4.6 (1M context)
ctx ⣄        5% (50k/1.0M) │ 5h ⣤        6% (2h55m) │ 7d ⣿⣿⣿⣤     44% (1d6h)
```

- **1行目**: モデル名
- **2行目**: コンテキスト使用量 (トークン数) / 5時間レート制限 (残り時間) / 7日レート制限 (残り時間)
- Braille ドットバーにグラデーション着色 (緑→黄→赤)

## ワークフロー

```
/init-project → /research → /codex-research-review
             → /plan      → /codex-plan-review
             → /implement → /codex-impl-review
```
