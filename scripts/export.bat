@echo off
setlocal

echo [deprecated] Use scripts\windows-terminal\export.bat instead.
call "%~dp0windows-terminal\export.bat" %*
exit /b %ERRORLEVEL%
