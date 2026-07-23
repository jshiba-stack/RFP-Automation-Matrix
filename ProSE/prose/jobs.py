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
    result = spreadsheet.update_spreadsheet(
        path, details,
        skip_on_lock=bool(cfg.get("shared_workbook")),
        protect_id=bool(cfg.get("protect_solicitation_column")),
    )
    if result.get("stale_lock_cleared"):
        log("NOTE: removed a leftover Excel lock file (~$...) that no program was "
            "using -- Excel was probably closed uncleanly. Scan continued normally.")
    if result.get("skipped_locked"):
        log("NOTE: workbook is open in Excel (shared library) -- scan NOT written "
            "to avoid a conflict copy; the next scheduled scan will merge once "
            "it's closed.")
    else:
        log(
            f"Spreadsheet updated: {result['new']} new, {result['updated']} updated, "
            f"{result['total_rows']} total rows"
        )
        if result.get("duplicates_removed"):
            log(f"  collapsed {result['duplicates_removed']} duplicate row(s) "
                "(same solicitation stored under an amendment/variant number)")
        if result.get("entities_decoded"):
            log(f"  decoded HTML entities (&#x27; etc.) in {result['entities_decoded']} "
                "older row(s)")
        if result.get("contacts_collapsed"):
            log(f"  tidied {result['contacts_collapsed']} older row(s) that listed "
                "the same contact twice")
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
