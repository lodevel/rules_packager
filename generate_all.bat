@echo off
setlocal

REM Project root is folder containing this .bat
set "REPO=%~dp0"

REM Make local package importable without install
set "PYTHONPATH=%REPO%src"

echo Using PYTHONPATH=%PYTHONPATH%
set "ARGS=%*"
if "%ARGS%"=="" (
  set "ARGS=--collect-rules --build-wheels --overwrite"
)

echo Running: %ARGS%
echo.
echo Examples:
echo   generate_all.bat
echo     ^(defaults to --collect-rules --build-wheels --overwrite^)
echo     Outputs:
echo       - output\config\rules\
echo       - output\config\wheels\
echo   generate_all.bat --collect-rules --overwrite
echo   generate_all.bat --build-wheels --ensure-pip
echo.

REM Prefer the Python launcher on Windows (py), fall back to python.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%REPO%tools\generate_all.py" %ARGS%
) else (
  python "%REPO%tools\generate_all.py" %ARGS%
)

if NOT %ERRORLEVEL%==0 (
  echo.
  echo ERROR: generate_all failed with code %ERRORLEVEL%.
  echo.
)

echo.
echo Done.
pause

endlocal
