"""Flask settings dashboard for ProSE.

Runs locally (default http://127.0.0.1:5000). Lets the user edit keywords,
both schedules, and email settings, and trigger a scan or email on demand.
Background scans/emails run in a worker thread so the UI stays responsive.
"""

from __future__ import annotations

import threading

from flask import Flask, flash, redirect, render_template, request, url_for

from . import config, emailer, jobs
from .scheduler import ProseScheduler

app = Flask(__name__)
app.secret_key = "prose-local-dashboard"  # local-only; not security-sensitive

# Shared scheduler instance (started by __main__).
scheduler = ProseScheduler()

# Simple in-memory status of the most recent manual action.
_action_lock = threading.Lock()
_action_status = {"running": False, "kind": None, "message": ""}


def _set_action(running: bool, kind: str | None, message: str):
    with _action_lock:
        _action_status.update(running=running, kind=kind, message=message)


def _run_in_thread(kind: str, func):
    def worker():
        _set_action(True, kind, f"{kind.capitalize()} in progress...")
        try:
            if kind == "scan":
                res = func()
                msg = f"Scan complete: {res['new']} new, {res['updated']} updated."
            else:
                info = func()
                msg = f"Email sent to {', '.join(info['recipients'])}."
            _set_action(False, kind, msg)
        except Exception as exc:  # noqa: BLE001
            _set_action(False, kind, f"{kind.capitalize()} failed: {exc}")

    threading.Thread(target=worker, daemon=True).start()


@app.route("/")
def index():
    cfg = config.load_config()
    state = config.load_state()
    with _action_lock:
        action = dict(_action_status)
    try:
        next_runs = scheduler.next_run_times()
    except Exception:  # noqa: BLE001 - scheduler may not be started in some contexts
        next_runs = {}
    return render_template(
        "dashboard.html",
        cfg=cfg,
        state=state,
        action=action,
        next_runs=next_runs,
        weekdays=config.WEEKDAYS,
        has_password=bool(config.get_smtp_password()),
        gmail_connected=emailer.gmail_connected(cfg),
    )


@app.route("/save", methods=["POST"])
def save():
    cfg = config.load_config()
    f = request.form

    # Keywords: one per line.
    keywords = [ln.strip() for ln in f.get("keywords", "").splitlines() if ln.strip()]
    cfg["keywords"] = keywords

    # Schedule 1 (scan)
    scan_h, scan_m = _parse_time(f.get("scan_time"), 6, 0)
    cfg["scan_schedule"] = {
        "mode": "every_12h" if f.get("scan_mode") == "every_12h" else "daily",
        "hour": scan_h,
        "minute": scan_m,
    }

    # Schedule 2 (email)
    email_h, email_m = _parse_time(f.get("email_time"), 8, 0)
    cfg["email_schedule"] = {
        "days": f.getlist("email_days") or ["Mon"],
        "hour": email_h,
        "minute": email_m,
    }

    # Email settings
    recipients = [r.strip() for r in f.get("recipients", "").replace(",", "\n").splitlines() if r.strip()]
    cfg["email"].update(
        method="smtp" if f.get("email_method") == "smtp" else "gmail_api",
        sender=f.get("sender", "").strip(),
        recipients=recipients,
        smtp_host=f.get("smtp_host", "smtp.gmail.com").strip() or "smtp.gmail.com",
        smtp_port=_int(f.get("smtp_port"), 587),
        subject=f.get("subject", "").strip() or cfg["email"].get("subject", "Scanned Professional Services"),
    )

    config.save_config(cfg)

    # Secret password (only update if a new value was typed).
    pw = f.get("app_password", "").strip()
    if pw and pw != "********":
        config.set_smtp_password(pw)

    try:
        scheduler.reschedule(cfg)
    except Exception:  # noqa: BLE001
        pass

    flash("Settings saved.", "success")
    return redirect(url_for("index"))


@app.route("/connect-gmail", methods=["POST"])
def connect_gmail():
    """Run the Gmail OAuth consent flow (opens a browser on this machine)."""
    cfg = config.load_config()
    try:
        addr = emailer.authorize_gmail(cfg)
        flash(f"Connected Gmail account: {addr or 'authorized'}.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Could not connect Gmail: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/scan-now", methods=["POST"])
def scan_now():
    _run_in_thread("scan", jobs.run_scan)
    flash("Scan started. Refresh in a minute to see results.", "info")
    return redirect(url_for("index"))


@app.route("/email-now", methods=["POST"])
def email_now():
    _run_in_thread("email", jobs.run_email)
    flash("Email send started.", "info")
    return redirect(url_for("index"))


@app.route("/status.json")
def status_json():
    with _action_lock:
        return dict(_action_status)


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_time(value, default_h, default_m):
    """Parse an <input type=time> 'HH:MM' (24h) value into (hour, minute)."""
    try:
        h_str, m_str = str(value).split(":")[:2]
        h, m = int(h_str), int(m_str)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (TypeError, ValueError, AttributeError):
        pass
    return default_h, default_m
