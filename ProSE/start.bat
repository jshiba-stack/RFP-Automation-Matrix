@echo off
REM ProSE launcher: sets up the virtual environment on first run, then starts
REM the dashboard + scheduler. Double-click this file to run ProSE.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment and installing dependencies...
  python -m venv .venv
  call ".venv\Scripts\python.exe" -m pip install --upgrade pip
  call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

call ".venv\Scripts\python.exe" run.py
pause
