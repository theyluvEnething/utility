@echo off
setlocal
set "RUNNER=%~dp0source/sh.bat"
for %%I in ("%RUNNER%") do set "RUNNER_ABS=%%~fI"
assoc .sh=ShScript >nul
ftype ShScript="%RUNNER_ABS%" "%%1" %%*
echo Associated .sh with %RUNNER_ABS%
endlocal