"""ProSE entry point.

Usage:
    python -m prose             Start the dashboard (default).
    python -m prose scan        Run a single scan now and exit (for manual/cron use).
    python -m prose email       Send the spreadsheet now and exit.
    python -m prose auth-email  Connect a Gmail account (opens browser consent).
    python -m prose unschedule  Remove the Windows scheduled tasks (kill switch).

The dashboard runs locally at http://127.0.0.1:5000.
"""

from __future__ import annotations

import sys
import threading
import webbrowser

from . import config, emailer, jobs, winsched

HOST = "127.0.0.1"
PORT = 5000


def main(argv: list[str]) -> int:
    config.load_env()  # pull PROSE_SMTP_PASSWORD from .env into the environment

    if len(argv) > 1 and argv[1] in ("scan", "email", "auth-email", "unschedule"):
        if argv[1] == "scan":
            jobs.run_scan()
        elif argv[1] == "auth-email":
            addr = emailer.authorize_gmail()
            print(f"Connected Gmail account: {addr or '(unknown)'}")
        elif argv[1] == "unschedule":
            winsched.remove_tasks()
            print("Removed ProSE scheduled tasks. No scans/emails will run until "
                  "you Save settings again.")
        else:
            jobs.run_email()
        return 0

    # Default: dashboard. On Windows the scheduler is the external Task Scheduler
    # (no in-process threads), so closing this window leaves nothing running but
    # the dormant scheduled tasks. On other platforms an in-process scheduler
    # runs only while this process is alive and is stopped in the finally block.
    from .app import app, scheduler

    scheduler.start()
    print(f"ProSE dashboard running at http://{HOST}:{PORT}  (Ctrl+C to stop)")
    # daemon=True so this helper thread never keeps the process alive on exit.
    opener = threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}"))
    opener.daemon = True
    opener.start()
    try:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
