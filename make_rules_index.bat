@echo off
setlocal

REM Project root is folder containing this .bat
set "REPO=%~dp0"

set "SCRIPT=%REPO%tools\make_rules_index.py"
set "ARGS=%*"

echo.
echo Updating rules_index.json for base pack
echo Script: %SCRIPT%
if "%ARGS%"=="" (
  echo Version: (auto-detect latest)
) else (
  echo Version: %ARGS%
)
echo.

REM Prefer the Python launcher on Windows (py), fall back to python.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT%" %ARGS%
) else (
  python "%SCRIPT%" %ARGS%
)

if NOT %ERRORLEVEL%==0 (
  echo.
  echo ERROR: make_rules_index failed with code %ERRORLEVEL%.
  echo.
)

echo.
echo Done.
endlocal
