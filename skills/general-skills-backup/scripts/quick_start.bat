@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PYTHON_CMD=python

where py >nul 2>nul
if %errorlevel%==0 (
  py "%SCRIPT_DIR%quick_start.py" %*
) else (
  %PYTHON_CMD% "%SCRIPT_DIR%quick_start.py" %*
)

endlocal
