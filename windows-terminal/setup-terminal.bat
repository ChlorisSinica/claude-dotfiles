@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "FEATURE=%~1"
set "ACTION=%~2"

if "%FEATURE%"=="" goto usage

if /i "%FEATURE%"=="git-bash-profile" (
    call "%SCRIPT_DIR%\_setup-git-bash-profile.bat" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

if /i "%FEATURE%"=="bell" (
    call "%SCRIPT_DIR%\_setup-terminal-bell.bat" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

if /i "%FEATURE%"=="git-bash-bell" (
    call "%SCRIPT_DIR%\_setup-git-bash-bell.bat" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

if /i "%FEATURE%"=="toast" (
    if /i "%ACTION%"=="enable" (
        call "%SCRIPT_DIR%\_setup-toast-notify.bat" --enable %3 %4 %5 %6 %7 %8 %9
        exit /b %ERRORLEVEL%
    )
    if /i "%ACTION%"=="disable" (
        call "%SCRIPT_DIR%\_setup-toast-notify.bat" --disable %3 %4 %5 %6 %7 %8 %9
        exit /b %ERRORLEVEL%
    )
    goto usage
)

:usage
echo Usage:
echo   %~nx0 git-bash-profile [options]
echo   %~nx0 bell [options]
echo   %~nx0 git-bash-bell [options]
echo   %~nx0 toast enable [project_dir] [--no-pause]
echo   %~nx0 toast disable [project_dir] [--no-pause]
exit /b 1
