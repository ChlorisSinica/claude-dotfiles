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

## ワークフロー

```
/init-project → /research → /codex-research-review
             → /plan      → /codex-plan-review
             → /implement → /codex-impl-review
```
