@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "MODE="
set "TARGET_DIR=%CD%"
set "FLAG_NO_PAUSE=0"
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:parse_args
if "%~1"=="" goto end_args
if /i "%~1"=="--enable" (
    set "MODE=enable"
    shift
    goto parse_args
)
if /i "%~1"=="--disable" (
    set "MODE=disable"
    shift
    goto parse_args
)
if /i "%~1"=="--no-pause" (
    set "FLAG_NO_PAUSE=1"
    shift
    goto parse_args
)
set "TARGET_DIR=%~1"
shift
goto parse_args
:end_args

if "%MODE%"=="" (
    echo Usage: %~nx0 --enable [project_dir]   (default: current dir)
    echo        %~nx0 --disable [project_dir]  (default: current dir)
    exit /b 1
)

echo ==========================================
echo  Setup Claude Code Toast Notify
echo ==========================================
echo.
echo Mode: %MODE%
echo Project: %TARGET_DIR%
echo.
if not "%FLAG_NO_PAUSE%"=="1" pause

pushd "%SCRIPT_DIR%"
set "HELPER=toast-notify\setup-toast-notify.ps1"
set "HELPER_PATH=%CD%\%HELPER%"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%HELPER_PATH%" -Mode "%MODE%" -TargetDir "%TARGET_DIR%"
set "SCRIPT_STATUS=%ERRORLEVEL%"
popd
if not "%SCRIPT_STATUS%"=="0" exit /b %SCRIPT_STATUS%

echo.
echo Process Done.
if not "%FLAG_NO_PAUSE%"=="1" pause
