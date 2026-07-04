"""High-level operations shared by the scheduler and the dashboard buttons."""

from __future__ import annotations

from datetime import datetime

from . import config, emailer, scanner, spreadsheet


def _now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def run_scan(cfg: dict | None = None, log=print) -> dict:
    """Scan all keywords, update the spreadsheet, record state.

    Returns the spreadsheet merge result plus counts.
    """
    cfg = cfg or config.load_config()
    keywords = [k for k in cfg.get("keywords", []) if k.strip()]
    log(f"Scan started: {len(keywords)} keyword(s)")
    details = scanner.scan(keywords, log=log)
    path = config.spreadsheet_abspath(cfg)
    result = spreadsheet.update_spreadsheet(path, details)
    log(
        f"Spreadsheet updated: {result['new']} new, {result['updated']} updated, "
        f"{result['total_rows']} total rows"
    )
    if result.get("diverted"):
        log(f"NOTE: workbook was open/locked -- results saved to {result['saved_to']}. "
            "Close Excel and re-run the scan to merge into the main file.")
    config.update_state(
        last_scan=_now_iso(),
        last_scan_count=len(details),
        last_scan_new=result["new"],
        last_error=None,
    )
    return result


def run_email(cfg: dict | None = None, log=print) -> dict:
    """Email the current spreadsheet to the recipient list."""
    cfg = cfg or config.load_config()
    log("Sending email...")
    info = emailer.send_spreadsheet(cfg)
    config.update_state(last_email=_now_iso())
    log(f"Email sent to: {', '.join(info['recipients'])}")
    return info
