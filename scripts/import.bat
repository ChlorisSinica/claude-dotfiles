@echo off
setlocal

echo [deprecated] Use scripts\windows-terminal\import.bat instead.
call "%~dp0windows-terminal\import.bat" %*
exit /b %ERRORLEVEL%
