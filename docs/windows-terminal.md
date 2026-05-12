# Windows Terminal

`windows-terminal/` 配下の補助スクリプト一覧です．

## 統合コマンド

```bat
~/claude-dotfiles/windows-terminal/setup-terminal.bat git-bash-profile # Git Bash profileの追加 (Windows Terminal設定は保持)

~/claude-dotfiles/windows-terminal/setup-terminal.bat bell # PowerShell / Windows PowerShell / Git Bash の bell を有効化

~/claude-dotfiles/windows-terminal/setup-terminal.bat pwsh # pwsh (PowerShell7)のインストール. インストール済みの場合skip, --forceで再インストール

~/claude-dotfiles/windows-terminal/setup-terminal.bat toast enable [project_dir] # 対象プロジェクトの .claude/settings.json に通知 hook を追加．project_dir 省略時はカレントディレクトリを使用

~/claude-dotfiles/windows-terminal/setup-terminal.bat toast disable [project_dir] # 対象プロジェクトの .claude/settings.json から通知 hook だけを削除．project_dir 省略時はカレントディレクトリを使用
```

## 設定同期

```bat
windows-terminal\import.bat
windows-terminal\export.bat
```

`windows-terminal/settings.json` と `windows-terminal/.inputrc` を snapshot として import / export します．
