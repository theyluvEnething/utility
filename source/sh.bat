@echo off 
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1"=="" (
    python "%SCRIPT_DIR%sh.py"
    set "EXIT_CODE=%ERRORLEVEL%"
    exit /b %EXIT_CODE%
)

set "SCRIPT_FILE=%~1"
shift
set "SCRIPT_ARGS=%*"

python "%SCRIPT_DIR%sh.py" "%SCRIPT_FILE%" %SCRIPT_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"
exit /b %EXIT_CODE%