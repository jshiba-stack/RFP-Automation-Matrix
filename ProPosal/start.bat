@echo off
REM ProPosal launcher: sets up the virtual environment on first run, then opens
REM the dashboard. Double-click this file to run ProPosal.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment and installing dependencies...
  python -m venv .venv
  call ".venv\Scripts\python.exe" -m pip install --upgrade pip
  call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

REM No subcommand launches the local web dashboard (opens your browser).
call ".venv\Scripts\python.exe" -m proposal %*
pause
