# Toast Notify Plan

## Objective

Windows 11 上で `Claude Code` を `Windows Terminal` + `Git Bash` または `PowerShell 7` で使う際、Claude Code の通知イベントを Win11 のトースト通知として表示できるようにする。

初期バージョンでは、通知の有効化・無効化を 1 本の `.bat` で切り替えられることを目標とする。

## Success Criteria

- `Notification(permission_prompt)` でトースト通知が出る
- `Notification(idle_prompt)` でトースト通知が出る
- `Stop` でトースト通知が出る
- `Stop` 通知は毎回出る
- 通知 ON の場合、トースト表示・音・開く動作がすべて有効になる
- 通知 OFF の場合、上記がすべて無効になる
- `Git Bash` / `pwsh` のどちらで Claude Code を起動しても動作する
- 有効化・無効化を再実行しても既存設定を壊さない
- 設定はプロジェクト単位の `.claude/settings.json` に対して行う

## Scope

- Claude Code hooks を使った Windows トースト通知
- 通知内容の整形
- 通知 ON/OFF の切り替え
- Windows Terminal を対象とした開く動作

## Out Of Scope

- 通知種別ごとの個別 ON/OFF
- 音だけ OFF などの個別設定
- `Approve` / `Deny` ボタン
- 権限承認の自動化
- 高度な通知履歴 UI

## Target Events

### Notification(permission_prompt)

- Claude Code がツール実行の許可を求めるとき
- 最重要通知
- タイトル例: `Claude Code: Permission Needed`
- 表示言語: 英語
- 表示場所: フォルダ名

### Notification(idle_prompt)

- Claude Code が一定時間入力待ちになったとき
- ユーザー復帰用の通知
- タイトル例: `Claude Code: Waiting For Input`
- 表示言語: 英語
- 表示場所: フォルダ名

### Stop

- Claude Code のメイン応答が完了したとき
- 毎ターンの作業完了通知
- タイトル例: `Claude Code: Response Complete`
- 表示言語: 英語
- 表示場所: フォルダ名

## UX Policy

- 通知設定は単一の ON/OFF のみ
- ON の場合:
  - トースト表示
  - 音
  - 開く動作
  をまとめて有効化する
- OFF の場合:
  - 上記すべてを無効化する

## Open Action

### Ideal Behavior

現在 Claude Code を実行している `Windows Terminal` ウィンドウを見つけて前面化する。

### Why This Is Preferred

- 新しい terminal を増やさない
- いま進行中のセッションに直接戻れる
- 通知からの復帰動線として最も自然

### Fallback Order

1. 既存の `Windows Terminal` ウィンドウを前面化する
2. 前面化に失敗した場合は何もしない

### Notes

- `wt.exe` は既存ウィンドウへのコマンド送信をサポートしているが、「今の Claude Code セッションそのもの」を厳密に再フォーカスできるとは限らない
- そのため、Win32 API を使った前面化ロジックを第一候補として検討する
- 最初のバージョンでは「前面化に失敗しても通知自体は成功」にする
- fallback で新規 terminal や Explorer は開かない

参考:
- [Windows Terminal command line arguments](https://learn.microsoft.com/en-us/windows/terminal/command-line-arguments)

## Dependency Policy

- third-party 依存は極力増やさない
- 初期バージョンでは `BurntToast` を前提にしない
- 通知本体は `PowerShell` で実装する
- 必要に応じて Windows 標準 API / .NET / Win32 を使用する

## Proposed Files

- `windows-terminal/_setup-toast-notify.bat`
  - `--enable` / `--disable` を受け取る互換用の個別入口
  - 主入口は `setup-terminal.bat`
- `windows-terminal/toast-notify/focus-terminal.ps1`
  - 既存 Windows Terminal 前面化の補助
- `windows-terminal/toast-notify/invoke-toast-target.ps1`
  - プロトコル起動を受けて前面化ヘルパーを呼ぶ
- `windows-terminal/toast-notify/notify-toast.ps1`
  - 各プロジェクトの `.claude/hooks/notify-toast.ps1` へコピーされる通知本体

## Configuration Strategy

- 主入口の `.bat` は 1 本だけ提供する
- 例:
  - `windows-terminal\setup-terminal.bat toast enable C:\path\to\project`
  - `windows-terminal\setup-terminal.bat toast disable C:\path\to\project`
- `.bat` は次を行う
  - 通知用スクリプトの存在確認
  - 対象プロジェクトの `.claude/settings.json` のバックアップ
  - 対象プロジェクトの hook 設定の有効化または無効化
  - 結果表示
- 設定はグローバルではなくプロジェクト単位で管理する

## Hook Strategy

- `Notification` hook:
  - `permission_prompt`
  - `idle_prompt`
  を通知する
- `Stop` hook:
  - 応答完了を通知する
- hook は副作用のみとし、Claude Code の挙動制御はしない

## Data To Show In Toast

- イベント種別
- 1 行サマリ
- フォルダ名
- 必要な場合のみ作業ディレクトリ
- 必要なら時刻
- 表示言語は英語とする

## Technical Risks

### Existing Window Focus

- 既存の `Windows Terminal` を一意に特定できない可能性がある
- Windows の foreground 制約で前面化が拒否される可能性がある

### Hook Configuration Safety

- 既存の `.claude/settings.json` または相当設定を壊さない更新が必要
- 追記型で行うか、専用の管理ブロックを作るかを決める必要がある

### Cross-Shell Invocation

- Claude Code が `Git Bash` 上でも `pwsh` 上でも、最終的に通知本体を確実に起動できる必要がある

## Implementation Plan

1. 通知設定の保存方式を決める
2. `setup-terminal.bat` から呼べる `_setup-toast-notify.bat` の有効化・無効化フローを実装する
3. `Notification` hook 用 `notify-toast.ps1` を実装する
4. `Stop` hook 用の入力整形を実装する
5. `focus-terminal.ps1` で既存 `Windows Terminal` 前面化を試す
6. 前面化失敗時の fallback を実装する
7. README または補助ドキュメントを追記する

## Verification Plan

1. `--enable` 実行で hook が有効になる
2. `permission_prompt` を人工的に発生させ、通知が出る
3. `idle_prompt` を発生させ、通知が出る
4. `Stop` で通知が出る
5. 通知クリックまたは既定アクションで既存 terminal 前面化を試す
6. `--disable` 実行で通知が止まる
7. `--enable` / `--disable` の再実行で設定破損が起きない

## Open Questions

- Claude Code 設定ファイルをどの粒度で編集するか
- 前面化対象 terminal の識別を `WindowsTerminal.exe` ベースにするか、タイトルや cwd も併用するか

## Task Breakdown

1. `settings.json` の管理方式を確定する
2. `windows-terminal/setup-toast-notify.bat` を作る
3. `windows-terminal/toast-notify/notify-toast.ps1` を作る
4. `windows-terminal/toast-notify/focus-terminal.ps1` を作る
5. `windows-terminal/toast-notify/invoke-toast-target.ps1` を作る
6. `--enable` で `.claude/hooks/` へ必要スクリプトを配置する処理を作る
7. `--enable` で `.claude/settings.json` に `Notification` / `Stop` hook を追加する処理を作る
8. `--disable` で通知用 hook だけを削除する処理を作る
9. 通知文言を `permission_prompt` / `idle_prompt` / `Stop` ごとに整える
10. 既存 `Windows Terminal` 前面化ロジックを実装する
11. README に導入手順と注意点を追記する

## Verification Checklist

- `--enable` で必要スクリプトが `.claude/hooks/` に配置される
- `--enable` で `.claude/settings.json` に通知 hook が追加される
- `--enable` の再実行で hook が重複しない
- `--disable` で通知 hook だけが削除される
- `--disable` の再実行でも壊れない
- `permission_prompt` で英語トーストが出る
- `idle_prompt` で英語トーストが出る
- `Stop` で毎回トーストが出る
- 通知にはフォルダ名が表示される
- 既存 `Windows Terminal` 前面化が成功する場合は前に出る
- 前面化に失敗してもエラーで Claude Code の処理を壊さない
