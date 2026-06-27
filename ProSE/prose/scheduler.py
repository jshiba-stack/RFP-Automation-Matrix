"""Scheduling for the scan (Schedule 1) and email (Schedule 2).

On **Windows** (the primary target), the schedule is driven by the Windows Task
Scheduler via :mod:`prose.winsched`: saving settings registers two tasks that
run ``run_task.bat scan`` / ``run_task.bat email``, so jobs fire **even when the
dashboard is closed** and survive reboots. The dashboard remains the single
place to edit the schedule.

On non-Windows platforms (dev/testing) it falls back to an in-process
APScheduler, which only runs while the dashboard process is alive.

Either way the public interface is identical: ``start``, ``shutdown``,
``reschedule``, ``next_run_times`` -- so the app and entry point don't care which
backend is active.
"""

from __future__ import annotations

from . import config, jobs, winsched

SCAN_JOB_ID = "prose-scan"
EMAIL_JOB_ID = "prose-email"


class ProseScheduler:
    def __init__(self):
        self._use_win = winsched.available()
        self._scheduler = None  # APScheduler instance (non-Windows only)
        self._started = False

    # -- lifecycle ----------------------------------------------------------
    def start(self):
        if self._use_win:
            self._started = True
            self.reschedule()  # ensure the Task Scheduler tasks exist/match config
            return
        self._ensure_apscheduler()
        if not self._started:
            self._scheduler.start()
            self._started = True
        self.reschedule()

    def shutdown(self):
        # Windows tasks intentionally persist after the dashboard exits.
        if self._use_win:
            return
        if self._scheduler is not None and self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    def reschedule(self, cfg: dict | None = None):
        """Rebuild both triggers from the current config."""
        cfg = cfg or config.load_config()
        if self._use_win:
            winsched.sync_tasks(cfg)
            return
        self._reschedule_apscheduler(cfg)

    # -- introspection (for the dashboard) ----------------------------------
    def next_run_times(self) -> dict:
        if self._use_win:
            return winsched.next_run_times()
        out = {}
        for jid in (SCAN_JOB_ID, EMAIL_JOB_ID):
            job = self._scheduler.get_job(jid) if self._scheduler else None
            out[jid] = (
                job.next_run_time.strftime("%Y-%m-%d %H:%M %Z")
                if job and job.next_run_time else "not scheduled"
            )
        return out

    # -- APScheduler fallback (non-Windows) ---------------------------------
    def _ensure_apscheduler(self):
        if self._scheduler is None:
            from apscheduler.schedulers.background import BackgroundScheduler

            self._scheduler = BackgroundScheduler()

    def _scan_job(self):
        try:
            jobs.run_scan()
        except Exception as exc:  # noqa: BLE001
            config.update_state(last_error=f"Scheduled scan failed: {exc}")

    def _email_job(self):
        try:
            jobs.run_email()
        except Exception as exc:  # noqa: BLE001
            config.update_state(last_error=f"Scheduled email failed: {exc}")

    def _reschedule_apscheduler(self, cfg: dict):
        from zoneinfo import ZoneInfo

        from apscheduler.triggers.cron import CronTrigger

        self._ensure_apscheduler()
        tz = ZoneInfo(cfg.get("timezone", "Pacific/Honolulu"))

        # Schedule 1: scan
        sc = cfg["scan_schedule"]
        minute = int(sc.get("minute", 0))
        hour = int(sc.get("hour", 6))
        if sc.get("mode") == "every_12h":
            hours = f"{hour % 24},{(hour + 12) % 24}"
            scan_trigger = CronTrigger(hour=hours, minute=minute, timezone=tz)
        else:  # daily
            scan_trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
        self._scheduler.add_job(
            self._scan_job, scan_trigger, id=SCAN_JOB_ID, replace_existing=True,
        )

        # Schedule 2: email
        ec = cfg["email_schedule"]
        email_trigger = CronTrigger(
            day_of_week=config.dow_tokens(ec.get("days", ["Mon"])),
            hour=int(ec.get("hour", 8)),
            minute=int(ec.get("minute", 0)),
            timezone=tz,
        )
        self._scheduler.add_job(
            self._email_job, email_trigger, id=EMAIL_JOB_ID, replace_existing=True,
        )
