"""ProSE entry point.

Usage:
    python -m prose            Start the dashboard + scheduler (default).
    python -m prose scan       Run a single scan now and exit (for manual/cron use).
    python -m prose email      Send the spreadsheet now and exit.
    python -m prose auth-email Connect a Gmail account (opens browser consent).

The dashboard runs locally at http://127.0.0.1:5000.
"""

from __future__ import annotations

import sys
import threading
import webbrowser

from . import config, emailer, jobs

HOST = "127.0.0.1"
PORT = 5000


def main(argv: list[str]) -> int:
    config.load_env()  # pull PROSE_SMTP_PASSWORD from .env into the environment

    if len(argv) > 1 and argv[1] in ("scan", "email", "auth-email"):
        if argv[1] == "scan":
            jobs.run_scan()
        elif argv[1] == "auth-email":
            addr = emailer.authorize_gmail()
            print(f"Connected Gmail account: {addr or '(unknown)'}")
        else:
            jobs.run_email()
        return 0

    # Default: dashboard + background scheduler.
    from .app import app, scheduler

    scheduler.start()
    print(f"ProSE dashboard running at http://{HOST}:{PORT}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    try:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
