# Claude Code Dotfiles

Claude Code × Codex 連携ワークフローのグローバル設定。

## セットアップ

```bash
git clone <this-repo> ~/claude-dotfiles
bash ~/claude-dotfiles/setup.sh
```

`~/.claude/` に以下がインストールされます:

- `commands/init-project.md` — `/init-project` グローバルコマンド
- `templates/project-init/` — プロジェクト初期化テンプレート

## 使い方

任意のプロジェクトで Claude Code を起動し:

```
/init-project python-pytorch
```

プリセット: `python`, `python-pytorch`, `typescript`, `rust`, `autohotkey-v2`

## ワークフロー

```
/init-project → /research → /codex-research-review
             → /plan      → /codex-plan-review
             → /implement → /codex-impl-review
```
