@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0tools\build_windows.ps1" -Clean -Onefile
exit /b %ERRORLEVEL%
