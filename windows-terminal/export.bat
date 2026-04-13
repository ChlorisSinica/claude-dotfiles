@echo off
chcp 65001 > nul
echo ==========================================
echo  ターミナル環境 設定エクスポートツール
echo ==========================================
echo.

echo 1/2: Windows Terminal の設定をコピーしています...
copy /Y "%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json" "%~dp0settings.json"

echo 2/2: Git Bash の設定（.inputrc）をコピーしています...
copy /Y "%USERPROFILE%\.inputrc" "%~dp0.inputrc"

echo.
echo エクスポートが完了しました！
echo 同じフォルダに作成されたファイルを新しいPCへ移行してください。
pause
