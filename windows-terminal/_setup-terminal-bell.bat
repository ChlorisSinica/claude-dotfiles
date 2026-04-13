@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "BELL_STYLE=all"
set "FLAG_UPDATE_INPUTRC=1"

:parse_args
if "%~1"=="" goto end_args
if /i "%~1"=="--taskbar-only" set "BELL_STYLE=taskbar"
if /i "%~1"=="--audible-only" set "BELL_STYLE=audible"
if /i "%~1"=="--window-only" set "BELL_STYLE=window"
if /i "%~1"=="--no-inputrc" set "FLAG_UPDATE_INPUTRC=0"
shift
goto parse_args
:end_args

echo ==========================================
echo  Setup Terminal Bell in Windows Terminal
echo ==========================================
echo.
echo This enables Windows Terminal bell notifications for PowerShell and Git Bash.
echo.
echo [Tasks]
echo  - Set Windows Terminal bellStyle to %BELL_STYLE% for default and common shell profiles
if %FLAG_UPDATE_INPUTRC%==1 (echo  - Update Git Bash .inputrc to use audible bell) else (echo  - Update Git Bash .inputrc: skipped)
echo.
pause

set "PSSCRIPT=%TEMP%\setup_terminal_bell_%RANDOM%%RANDOM%.ps1"
call :write_ps_header
call :write_defaults_block
call :write_profile_block
call :write_ps_footer

powershell -NoProfile -ExecutionPolicy Bypass -File "%PSSCRIPT%"
set "SCRIPT_STATUS=%ERRORLEVEL%"
del "%PSSCRIPT%" > nul 2>&1
if not "%SCRIPT_STATUS%"=="0" exit /b %SCRIPT_STATUS%

if %FLAG_UPDATE_INPUTRC%==1 (
    echo.
    echo [2] Updating .inputrc...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$path = Join-Path $env:USERPROFILE '.inputrc';" ^
        "$line = 'set bell-style audible';" ^
        "if (Test-Path -LiteralPath $path) {" ^
        "  $content = Get-Content -LiteralPath $path -ErrorAction Stop;" ^
        "  $updated = $false;" ^
        "  $content = @($content | ForEach-Object {" ^
        "    if ($_ -match '^\s*set\s+bell-style\s+\S+\s*$') { $updated = $true; $line } else { $_ }" ^
        "  });" ^
        "  if (-not $updated) { $content += $line };" ^
        "  Set-Content -LiteralPath $path -Value $content -Encoding ASCII;" ^
        "} else {" ^
        "  Set-Content -LiteralPath $path -Value $line -Encoding ASCII;" ^
        "}" ^
        "Write-Host ' [+] .inputrc updated to audible bell.' -ForegroundColor Cyan"
    if errorlevel 1 exit /b %ERRORLEVEL%
)

echo.
echo Process Done.
echo If Claude Code should ring the terminal bell, set:
echo   claude config set --global preferredNotifChannel terminal_bell
pause
goto :eof

:write_ps_header
> "%PSSCRIPT%" echo $path = Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json'
>> "%PSSCRIPT%" echo if (-not (Test-Path $path)) { Write-Host "settings.json was not found." -ForegroundColor Red; exit 1 }
>> "%PSSCRIPT%" echo $json = Get-Content -LiteralPath $path -Raw -Encoding UTF8 ^| ConvertFrom-Json
>> "%PSSCRIPT%" echo if (-not $json.profiles) { Write-Host "profiles section was not found." -ForegroundColor Red; exit 1 }
>> "%PSSCRIPT%" echo if (-not $json.profiles.list) { Write-Host "profiles.list was not found." -ForegroundColor Red; exit 1 }
>> "%PSSCRIPT%" echo $style = "%BELL_STYLE%"
exit /b

:write_defaults_block
>> "%PSSCRIPT%" echo if (-not $json.profiles.defaults) { $json.profiles ^| Add-Member -MemberType NoteProperty -Name "defaults" -Value ([PSCustomObject]@{}) }
>> "%PSSCRIPT%" echo $json.profiles.defaults ^| Add-Member -MemberType NoteProperty -Name "bellStyle" -Value $style -Force
>> "%PSSCRIPT%" echo Write-Host (" [+] profiles.defaults bellStyle set to " + $style + ".") -ForegroundColor Cyan
exit /b

:write_profile_block
>> "%PSSCRIPT%" echo foreach ($p in $json.profiles.list) {
>> "%PSSCRIPT%" echo     $name = [string]$p.name
>> "%PSSCRIPT%" echo     $source = [string]$p.source
>> "%PSSCRIPT%" echo     $commandline = [string]$p.commandline
>> "%PSSCRIPT%" echo     $isGitBash = $name -eq "Git Bash" -or $commandline -match '\\Git\\bin\\bash\.exe'
>> "%PSSCRIPT%" echo     $isPwsh = $source -eq "Windows.Terminal.PowershellCore" -or $commandline -match '(^|\\)pwsh\.exe' -or $name -eq "PowerShell"
>> "%PSSCRIPT%" echo     $isWindowsPowerShell = $name -eq "Windows PowerShell" -or $commandline -match 'WindowsPowerShell\\v1\.0\\powershell\.exe'
>> "%PSSCRIPT%" echo     if ($isGitBash -or $isPwsh -or $isWindowsPowerShell) {
>> "%PSSCRIPT%" echo         $p ^| Add-Member -MemberType NoteProperty -Name "bellStyle" -Value $style -Force
>> "%PSSCRIPT%" echo         Write-Host (" [+] " + $name + " bellStyle set to " + $style + ".") -ForegroundColor Cyan
>> "%PSSCRIPT%" echo     }
>> "%PSSCRIPT%" echo }
exit /b

:write_ps_footer
>> "%PSSCRIPT%" echo $json ^| ConvertTo-Json -Depth 20 ^| Set-Content -LiteralPath $path -Encoding UTF8
exit /b
