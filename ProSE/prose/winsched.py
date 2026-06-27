"""Windows Task Scheduler integration for ProSE.

The dashboard registers two scheduled tasks via ``schtasks`` so that scans and
emails fire **even when the dashboard is closed** (and survive reboots):

  * ``ProSE-Scan``  -> ``run_task.bat scan``
  * ``ProSE-Email`` -> ``run_task.bat email``

Tasks are (re)created from the current config every time settings are saved, so
the dashboard stays the single source of truth for the schedule. Times are
interpreted by Windows in the **machine's local time zone** (see note in the
README) -- not the ``timezone`` field in config.json.

Tasks are created for the current user and run only when that user is logged on,
which needs no administrator rights. To run while logged off you would re-create
them with ``/RU``/``/RP`` (a stored password) -- intentionally not done here.
"""

from __future__ import annotations

import subprocess
import sys

from . import config

# Task names (as they appear in Task Scheduler) and the dashboard dict keys.
SCAN_TASK = "ProSE-Scan"
EMAIL_TASK = "ProSE-Email"
SCAN_KEY = "prose-scan"
EMAIL_KEY = "prose-email"

# config.WEEKDAYS ("Sun".."Sat") -> schtasks /D tokens.
_DOW_SCHTASKS = {
    "Sun": "SUN", "Mon": "MON", "Tue": "TUE", "Wed": "WED",
    "Thu": "THU", "Fri": "FRI", "Sat": "SAT",
}


def available() -> bool:
    """True only on Windows (where ``schtasks`` exists)."""
    return sys.platform == "win32"


def _wrapper_path() -> str:
    """Absolute path to run_task.bat at the project root."""
    return str(config.ROOT / "run_task.bat")


def _run(args: list[str]) -> subprocess.CompletedProcess:
    """Invoke schtasks without popping a console window."""
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        ["schtasks", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )


def _hhmm(hour: int, minute: int) -> str:
    return f"{int(hour):02d}:{int(minute):02d}"


def _create_scan_task(cfg: dict) -> None:
    sc = cfg["scan_schedule"]
    start = _hhmm(sc.get("hour", 6), sc.get("minute", 0))
    tr = f'"{_wrapper_path()}" scan'
    if sc.get("mode") == "every_12h":
        # HOURLY /MO 12 starting at `start` fires at start and start+12h.
        sched = ["/SC", "HOURLY", "/MO", "12", "/ST", start]
    else:
        sched = ["/SC", "DAILY", "/ST", start]
    _run(["/Create", "/TN", SCAN_TASK, "/TR", tr, *sched, "/F"])


def _create_email_task(cfg: dict) -> None:
    ec = cfg["email_schedule"]
    start = _hhmm(ec.get("hour", 8), ec.get("minute", 0))
    days = [_DOW_SCHTASKS[d] for d in ec.get("days", ["Mon"]) if d in _DOW_SCHTASKS]
    if not days:
        days = ["MON"]
    tr = f'"{_wrapper_path()}" email'
    _run([
        "/Create", "/TN", EMAIL_TASK, "/TR", tr,
        "/SC", "WEEKLY", "/D", ",".join(days), "/ST", start, "/F",
    ])


def sync_tasks(cfg: dict | None = None) -> None:
    """(Re)create both scheduled tasks from the current config. Idempotent."""
    if not available():
        return
    cfg = cfg or config.load_config()
    _create_scan_task(cfg)
    _create_email_task(cfg)


def remove_tasks() -> None:
    """Delete both ProSE scheduled tasks (used for uninstall/cleanup)."""
    if not available():
        return
    for name in (SCAN_TASK, EMAIL_TASK):
        _run(["/Delete", "/TN", name, "/F"])


def _next_run_for(task: str) -> str:
    """Parse 'Next Run Time' from schtasks /Query for one task."""
    proc = _run(["/Query", "/TN", task, "/FO", "LIST"])
    if proc.returncode != 0:
        return "not scheduled"
    for line in proc.stdout.splitlines():
        if line.strip().lower().startswith("next run time:"):
            value = line.split(":", 1)[1].strip()
            # schtasks prints "N/A" when a one-time/expired task has no next run.
            return value if value and value.upper() != "N/A" else "not scheduled"
    return "not scheduled"


def next_run_times() -> dict:
    """Next-run times keyed to match the dashboard (prose-scan / prose-email)."""
    if not available():
        return {SCAN_KEY: "not scheduled", EMAIL_KEY: "not scheduled"}
    return {
        SCAN_KEY: _next_run_for(SCAN_TASK),
        EMAIL_KEY: _next_run_for(EMAIL_TASK),
    }
