@echo off
chcp 65001 > nul
echo ==========================================
echo  ターミナル環境 設定インポートツール
echo ==========================================
echo.

rem ファイルの存在確認
if not exist "%~dp0settings.json" (
    echo [エラー] 同じフォルダに settings.json が見つかりません。
    pause
    exit /b
)
if not exist "%~dp0.inputrc" (
    echo [エラー] 同じフォルダに .inputrc が見つかりません。
    pause
    exit /b
)

echo 1/2: Windows Terminal の設定を適用中...
copy /Y "%~dp0settings.json" "%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"

echo 2/2: Git Bash の設定（.inputrc）を適用中...
copy /Y "%~dp0.inputrc" "%USERPROFILE%\.inputrc"

echo.
echo インポートが完了しました！
echo Windows Terminalを起動して設定が反映されているか確認してください。
pause
