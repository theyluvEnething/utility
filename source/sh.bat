@echo off
setlocal enabledelayedexpansion
if "%~1"=="" (
  echo No script specified.
  exit /b 1
)
set "SCRIPT=%~f1"
shift
set "ARGS=%*"
for %%P in ("%SCRIPT%") do set "SCRIPTDIR=%%~dpP"
pushd "%SCRIPTDIR%"
where wsl.exe >nul 2>&1
if %errorlevel%==0 goto use_wsl
if exist "%ProgramFiles%\Git\bin\bash.exe" set "GITBASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined GITBASH if exist "%ProgramFiles%\Git\usr\bin\bash.exe" set "GITBASH=%ProgramFiles%\Git\usr\bin\bash.exe"
if not defined GITBASH if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "GITBASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if defined GITBASH goto use_gitbash
where bash >nul 2>&1
if %errorlevel%==0 (
  for /f "delims=" %%B in ('where bash') do set "GITBASH=%%B"
  goto use_gitbash
)
goto fallback
:use_wsl
for /f "usebackq delims=" %%i in (`wsl.exe wslpath -a "%SCRIPT%"`) do set "WSL_PATH=%%i"
wsl.exe bash -lc "bash \"$WSL_PATH\" %ARGS%"
set "CODE=%ERRORLEVEL%"
popd
exit /b %CODE%
:use_gitbash
"%GITBASH%" --login -i "%SCRIPT%" %ARGS%
set "CODE=%ERRORLEVEL%"
popd
exit /b %CODE%
:fallback
python "%~dp0sh.py" "%SCRIPT%" %ARGS%
set "CODE=%ERRORLEVEL%"
popd
exit /b %CODE%