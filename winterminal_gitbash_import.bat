@echo off
setlocal

echo [deprecated] Use scripts\windows-terminal\setup-git-bash-profile.bat instead.
call "%~dp0scripts\windows-terminal\setup-git-bash-profile.bat" %*
exit /b %ERRORLEVEL%
