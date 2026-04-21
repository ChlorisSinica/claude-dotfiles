@echo off
setlocal EnableExtensions DisableDelayedExpansion

echo ==========================================
echo  Setup PowerShell 7 (pwsh)
echo ==========================================
echo.

set "FLAG_NO_PAUSE=0"
set "FLAG_FORCE=0"

:parse_args
if "%~1"=="" goto end_args
if /i "%~1"=="--no-pause" (
    set "FLAG_NO_PAUSE=1"
    shift
    goto parse_args
)
if /i "%~1"=="--force" (
    set "FLAG_FORCE=1"
    shift
    goto parse_args
)
echo Unknown argument: %~1
echo Usage: %~nx0 [--no-pause] [--force]
exit /b 1
:end_args

echo [Tasks]
echo  - Check if pwsh is installed
if %FLAG_FORCE%==1 (
    echo  - Force reinstall via winget
) else (
    echo  - Install Microsoft.PowerShell via winget if missing
)
echo.
if not "%FLAG_NO_PAUSE%"=="1" pause

echo [1] Checking existing pwsh...
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    if %FLAG_FORCE%==0 (
        echo  [-] pwsh is already installed.
        pwsh -NoProfile -Command "Write-Host ('     Version: ' + $PSVersionTable.PSVersion.ToString())"
        goto done
    )
    echo  [!] pwsh is already installed, but --force was specified.
) else (
    echo  [+] pwsh not found.
)

echo.
echo [2] Checking winget...
where winget >nul 2>&1
if not %ERRORLEVEL%==0 (
    echo.
    echo ERROR: winget was not found on PATH.
    echo Install "App Installer" from the Microsoft Store, or install PowerShell 7 manually:
    echo   https://github.com/PowerShell/PowerShell/releases
    if not "%FLAG_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo.
echo [3] Installing Microsoft.PowerShell via winget...
winget install --id Microsoft.PowerShell -e --silent --accept-source-agreements --accept-package-agreements
set "INSTALL_STATUS=%ERRORLEVEL%"
if not "%INSTALL_STATUS%"=="0" (
    echo.
    echo ERROR: winget install failed with exit code %INSTALL_STATUS%.
    if not "%FLAG_NO_PAUSE%"=="1" pause
    exit /b %INSTALL_STATUS%
)

echo.
echo  [+] pwsh installation completed.
echo  Note: Open a new terminal for the PATH update to take effect.
echo        Windows Terminal auto-detects pwsh on next launch.

:done
echo.
echo Process Done.
if not "%FLAG_NO_PAUSE%"=="1" pause
