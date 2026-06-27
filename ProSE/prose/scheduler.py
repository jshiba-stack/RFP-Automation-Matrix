"""APScheduler jobs for the scan (Schedule 1) and email (Schedule 2).

All triggers run in the configured timezone (default Pacific/Honolulu / HST).
The scheduler is reconfigured live whenever settings change in the dashboard.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config, jobs

SCAN_JOB_ID = "prose-scan"
EMAIL_JOB_ID = "prose-email"


class ProseScheduler:
    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._started = False

    # -- lifecycle ----------------------------------------------------------
    def start(self):
        if not self._started:
            self._scheduler.start()
            self._started = True
        self.reschedule()

    def shutdown(self):
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    # -- jobs ---------------------------------------------------------------
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

    def reschedule(self, cfg: dict | None = None):
        """Rebuild both triggers from the current config."""
        cfg = cfg or config.load_config()
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

    # -- introspection (for the dashboard) ----------------------------------
    def next_run_times(self) -> dict:
        out = {}
        for jid in (SCAN_JOB_ID, EMAIL_JOB_ID):
            job = self._scheduler.get_job(jid)
            out[jid] = (
                job.next_run_time.strftime("%Y-%m-%d %H:%M %Z")
                if job and job.next_run_time else "not scheduled"
            )
        return out
