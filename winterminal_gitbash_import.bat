@echo off
setlocal EnableExtensions DisableDelayedExpansion

echo ==========================================
echo  Setup Git Bash to Windows Terminal
echo ==========================================
echo.

rem Default flags
set "FLAG_GIT_INSTALL=0"
set "FLAG_ADD_BASH=1"
set "FLAG_SET_FONT=1"

rem Parse args
:parse_args
if "%~1"=="" goto end_args
if /i "%~1"=="--install-git" set "FLAG_GIT_INSTALL=1"
if /i "%~1"=="--no-bash" set "FLAG_ADD_BASH=0"
if /i "%~1"=="--no-font" set "FLAG_SET_FONT=0"
shift
goto parse_args
:end_args

echo [Tasks]
if %FLAG_GIT_INSTALL%==1 (echo  - Auto-install Git: enabled) else (echo  - Auto-install Git: disabled)
if %FLAG_ADD_BASH%==1 (echo  - Add Git Bash profile: enabled) else (echo  - Add Git Bash profile: disabled)
if %FLAG_SET_FONT%==1 (echo  - Set font size to 14: enabled) else (echo  - Set font size to 14: disabled)
echo.
pause

if %FLAG_GIT_INSTALL%==1 (
    echo [1] Installing Git...
    winget install --id Git.Git -e --silent
    if errorlevel 1 exit /b %ERRORLEVEL%
)

set "PSSCRIPT=%TEMP%\setup_terminal_%RANDOM%%RANDOM%.ps1"
call :write_ps_header
if %FLAG_ADD_BASH%==1 call :write_git_bash_block
if %FLAG_SET_FONT%==1 call :write_font_block
call :write_ps_footer

powershell -NoProfile -ExecutionPolicy Bypass -File "%PSSCRIPT%"
set "SCRIPT_STATUS=%ERRORLEVEL%"
del "%PSSCRIPT%" > nul 2>&1
if not "%SCRIPT_STATUS%"=="0" exit /b %SCRIPT_STATUS%

echo.
echo [2] Checking .inputrc...
findstr /C:"set bell-style none" "%USERPROFILE%\.inputrc" > nul 2>&1
if errorlevel 1 (
    echo set bell-style none>> "%USERPROFILE%\.inputrc"
    echo  [+] Added bell disable setting.
) else (
    echo  [-] Bell disable setting already exists.
)

echo.
echo Process Done.
pause
goto :eof

:write_ps_header
> "%PSSCRIPT%" echo $path = Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json'
>> "%PSSCRIPT%" echo if (-not (Test-Path $path)) { Write-Host "settings.json was not found." -ForegroundColor Red; exit 1 }
>> "%PSSCRIPT%" echo $json = Get-Content -LiteralPath $path -Raw -Encoding UTF8 ^| ConvertFrom-Json
exit /b

:write_git_bash_block
>> "%PSSCRIPT%" echo $gitBashExists = $false
>> "%PSSCRIPT%" echo foreach ($p in $json.profiles.list) { if ($p.name -eq "Git Bash") { $gitBashExists = $true; break } }
>> "%PSSCRIPT%" echo if (-not $gitBashExists) {
>> "%PSSCRIPT%" echo     $newProfile = [PSCustomObject]@{ name="Git Bash"; commandline="C:\Program Files\Git\bin\bash.exe -i -l"; icon="C:\Program Files\Git\mingw64\share\git\git-for-windows.ico"; startingDirectory="%%USERPROFILE%%" }
>> "%PSSCRIPT%" echo     $json.profiles.list = @($json.profiles.list) + $newProfile
>> "%PSSCRIPT%" echo     Write-Host " [+] Git Bash profile added." -ForegroundColor Cyan
>> "%PSSCRIPT%" echo } else {
>> "%PSSCRIPT%" echo     Write-Host " [-] Git Bash profile already exists." -ForegroundColor Yellow
>> "%PSSCRIPT%" echo }
exit /b

:write_font_block
>> "%PSSCRIPT%" echo if (-not $json.profiles.defaults) { $json.profiles ^| Add-Member -MemberType NoteProperty -Name "defaults" -Value ([PSCustomObject]@{}) }
>> "%PSSCRIPT%" echo if (-not $json.profiles.defaults.font) { $json.profiles.defaults ^| Add-Member -MemberType NoteProperty -Name "font" -Value ([PSCustomObject]@{}) }
>> "%PSSCRIPT%" echo $json.profiles.defaults.font ^| Add-Member -MemberType NoteProperty -Name "size" -Value 14.0 -Force
>> "%PSSCRIPT%" echo Write-Host " [+] Font size set to 14." -ForegroundColor Cyan
exit /b

:write_ps_footer
>> "%PSSCRIPT%" echo $json ^| ConvertTo-Json -Depth 20 ^| Set-Content -LiteralPath $path -Encoding UTF8
exit /b

