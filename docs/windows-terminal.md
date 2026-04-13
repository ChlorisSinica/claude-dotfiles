# Windows Terminal

`windows-terminal/` 配下の補助スクリプト一覧です。

## 統合入口

```bat
windows-terminal\setup-terminal.bat git-bash-profile
windows-terminal\setup-terminal.bat bell
windows-terminal\setup-terminal.bat toast enable C:\path\to\project
windows-terminal\setup-terminal.bat toast disable C:\path\to\project
```

## 個別入口

`windows-terminal/_setup-git-bash-profile.bat`

- 既存の Windows Terminal 設定を保持したまま Git Bash profile を追加

`windows-terminal/_setup-terminal-bell.bat`

- PowerShell / Windows PowerShell / Git Bash の bell を有効化

`windows-terminal/_setup-toast-notify.bat --enable [project_dir]`

- 対象プロジェクトの `.claude/settings.json` に通知 hook を追加

`windows-terminal/_setup-toast-notify.bat --disable [project_dir]`

- 通知用 hook だけを削除

`windows-terminal/_setup-git-bash-bell.bat`

- Git Bash の bell だけを個別に有効化

## 設定同期

```bat
windows-terminal\import.bat
windows-terminal\export.bat
```

`windows-terminal/settings.json` と `windows-terminal/.inputrc` を snapshot として import / export します。
