@echo off
setlocal EnableExtensions DisableDelayedExpansion

echo ==========================================
echo  Setup Git Bash Bell in Windows Terminal
echo ==========================================
echo.
echo This enables Windows Terminal bell notifications for Git Bash.
echo Default behavior:
echo  - Windows Terminal profile: bellStyle = all
echo  - Git Bash inputrc: set bell-style audible
echo.
pause

set "PSSCRIPT=%TEMP%\setup_git_bash_bell_%RANDOM%%RANDOM%.ps1"
call :write_ps_header
call :write_git_bash_block
call :write_ps_footer

powershell -NoProfile -ExecutionPolicy Bypass -File "%PSSCRIPT%"
set "SCRIPT_STATUS=%ERRORLEVEL%"
del "%PSSCRIPT%" > nul 2>&1
if not "%SCRIPT_STATUS%"=="0" exit /b %SCRIPT_STATUS%

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
exit /b

:write_git_bash_block
>> "%PSSCRIPT%" echo $gitBash = $null
>> "%PSSCRIPT%" echo foreach ($p in $json.profiles.list) { if ($p.name -eq "Git Bash") { $gitBash = $p; break } }
>> "%PSSCRIPT%" echo if (-not $gitBash) {
>> "%PSSCRIPT%" echo     $gitBash = [PSCustomObject]@{ guid="{629768af-7857-4590-bac5-6504603b06eb}"; name="Git Bash"; commandline="C:\Program Files\Git\bin\bash.exe -i -l"; icon="C:\Program Files\Git\mingw64\share\git\git-for-windows.ico"; startingDirectory="%%USERPROFILE%%"; hidden=$false; bellStyle="all" }
>> "%PSSCRIPT%" echo     $json.profiles.list = @($json.profiles.list) + $gitBash
>> "%PSSCRIPT%" echo     Write-Host " [+] Git Bash profile added with bellStyle=all." -ForegroundColor Cyan
>> "%PSSCRIPT%" echo } else {
>> "%PSSCRIPT%" echo     $gitBash ^| Add-Member -MemberType NoteProperty -Name "bellStyle" -Value "all" -Force
>> "%PSSCRIPT%" echo     Write-Host " [+] Git Bash bellStyle set to all." -ForegroundColor Cyan
>> "%PSSCRIPT%" echo }
exit /b

:write_ps_footer
>> "%PSSCRIPT%" echo $json ^| ConvertTo-Json -Depth 20 ^| Set-Content -LiteralPath $path -Encoding UTF8
exit /b
