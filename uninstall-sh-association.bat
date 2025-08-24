@echo off
setlocal
set "TYPE="
for /f "tokens=2 delims==" %%A in ('assoc .sh 2^>nul') do set "TYPE=%%A"
set "CLEARED_EXT=0"
set "CLEARED_TYPE=0"
if /i "%TYPE%"=="ShScript" (
  assoc .sh=
  set "CLEARED_EXT=1"
)
ftype ShScript >nul 2>&1
if %errorlevel%==0 (
  ftype ShScript=
  set "CLEARED_TYPE=1"
)
if "%CLEARED_EXT%"=="1" (
  if "%CLEARED_TYPE%"=="1" (
    echo Removed .sh association and ShScript file type.
  ) else (
    echo Removed .sh association.
  )
) else (
  if "%CLEARED_TYPE%"=="1" (
    echo Removed ShScript file type.
  ) else (
    echo Nothing to remove.
  )
)
endlocal
exit /b 0