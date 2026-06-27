@echo off
REM ----------------------------------------------------------------------------
REM Wrapper invoked by Windows Task Scheduler to run a single ProSE job and exit.
REM   run_task.bat scan    -> python -m prose scan
REM   run_task.bat email   -> python -m prose email
REM The dashboard registers/updates the scheduled tasks that call this file, so
REM scans/emails fire even when the dashboard is closed. (PC must be on + the
REM task's user logged on, unless you configure the task to run logged-off.)
REM ----------------------------------------------------------------------------
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m prose %1
) else (
  python -m prose %1
)
