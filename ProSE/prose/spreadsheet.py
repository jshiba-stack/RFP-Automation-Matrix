"""Read/update the styled Excel workbook.

Design goals (from the spec):
  * 14 columns, fixed left-to-right order.
  * The program only ever fills the 9 DATA columns; the 5 MANUAL columns
    (Status, Pursue, Emailed, Status, Entered SF) are owned by the user and are
    preserved across runs (matched by Solicitation #).
  * De-duplicate by Solicitation #. New solicitations are inserted at the TOP
    (most-recent first); existing ones have their data fields refreshed in place
    without touching the manual columns.
  * Professional styling (borders, alignment, header colour scheme, banding,
    frozen header) is applied automatically and consistently every run, so the
    cosmetics never have to be set up by hand.

Manual-value preservation is done by reading every existing row into memory
keyed by Solicitation #, then rewriting the data area -- this avoids openpyxl's
insert_rows() style-loss pitfalls while keeping the user's typed values.
"""

from __future__ import annotations

import re
from copy import copy
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.protection import SheetProtection

# Column layout (1-based). Order matches the spec exactly.
HEADERS = [
    "Status",            # 1  manual
    "Solicitation #",    # 2  data
    "Organization",      # 3  data
    "Solicitation Title",  # 4 data
    "Published",         # 5  data
    "Due Date",          # 6  data
    "Pursue",            # 7  manual
    "Emailed",           # 8  manual
    "Status",            # 9  manual (second Status)
    "Entered SF",        # 10 manual
    "Contact Name",      # 11 data
    "Phone",             # 12 data
    "Email",             # 13 data
    "Keyword",           # 14 data (keyword(s) that matched the row)
]

SOLICITATION_COL = 2  # column B holds the dedupe key
DUE_COL = 6           # column F holds the Due Date (used for expiry sorting)

# Due dates arrive as "MM/DD/YYYY hh:mm AM/PM" (HANDS/HiePRO), occasionally as a
# bare "MM/DD/YYYY". A trailing timezone token (HST/HDT) is tolerated.
_DUE_FORMATS = ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M%p", "%m/%d/%Y")


def _parse_due(value) -> datetime | None:
    """Parse a Due Date cell into a datetime, or None if it can't be read.

    A date with no time is treated as the *end* of that day, so a solicitation
    stays active through its whole due date.
    """
    text = re.sub(r"\s+(HST|HDT|HAST|PST|PDT)$", "", str(value or "").strip(), flags=re.I)
    if not text:
        return None
    for fmt in _DUE_FORMATS:
        try:
            due = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == "%m/%d/%Y":
            due = due.replace(hour=23, minute=59, second=59)
        return due
    return None


def _is_expired(due_value, now: datetime) -> bool:
    """True when ``now`` is past the parsed due date. Unparseable dates are
    treated as NOT expired (never hide a row we can't confidently read)."""
    due = _parse_due(due_value)
    return due is not None and now > due

# Map parser field -> column index.
FIELD_TO_COL = {
    "solicitation_number": 2,
    "organization": 3,
    "title": 4,
    "published": 5,
    "due_date": 6,
    "contact_name": 11,
    "phone": 12,
    "email": 13,
    "keyword": 14,
}

COLUMN_WIDTHS = {
    1: 12, 2: 16, 3: 20, 4: 46, 5: 13, 6: 20,
    7: 10, 8: 10, 9: 12, 10: 12, 11: 20, 12: 16, 13: 28, 14: 22,
}

# --- styling palette --------------------------------------------------------
HEADER_FILL = PatternFill("solid", fgColor="1F4E5F")   # deep teal
BAND_FILL = PatternFill("solid", fgColor="EAF1F4")     # light teal banding
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
DATA_FONT = Font(name="Calibri", size=11, color="222222")
# Expired solicitations (past their due date) are struck through and greyed.
EXPIRED_FONT = Font(name="Calibri", size=11, color="9A9A9A", strike=True)
# Cell locking (only enforced by Excel once the sheet is protected). Used to
# make the Solicitation # column read-only while everything else stays editable.
LOCKED = Protection(locked=True)
UNLOCKED = Protection(locked=False)
_THIN = Side(style="thin", color="BFC9CE")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=False)
CENTER_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)
SHEET_TITLE = "Scanned Professional Services"


def _side_sig(side) -> tuple | None:
    """A comparable signature (style, color) for one cell-border side, or None
    when the side has no visible border."""
    if side is None or not side.style:
        return None
    color = getattr(side.color, "rgb", None) if side.color else None
    return (side.style, color)


def _border_sig(border) -> tuple:
    return tuple(_side_sig(s) for s in (border.left, border.right, border.top, border.bottom))


def _detect_border(ws):
    """Return the *dominant* cell border the user has applied to the existing
    grid (header + data), so a rewrite preserves their chosen border weight and
    colour instead of forcing the program's default. ``None`` when the sheet has
    no visibly bordered cells (fresh/blank), in which case callers fall back to
    the default ``BORDER``.

    We reuse the single most common border across all cells rather than a
    per-cell copy, because rows are reordered on every write — a uniform border
    (which is what "a box around every cell" produces) survives that faithfully
    and is applied to newly-added rows too.
    """
    from collections import Counter

    counts: Counter = Counter()
    representative: dict = {}
    for r in range(1, ws.max_row + 1):
        for c in range(1, len(HEADERS) + 1):
            border = ws.cell(row=r, column=c).border
            sig = _border_sig(border)
            if any(sig):  # at least one side is a visible border
                counts[sig] += 1
                # copy() unwraps openpyxl's StyleProxy into a real, assignable
                # Border (a proxy can't be set back onto another cell).
                representative.setdefault(sig, copy(border))
    if not counts:
        return None
    return representative[counts.most_common(1)[0][0]]


def _apply_protection(ws, protect_id: bool) -> None:
    """Turn the Solicitation # column read-only via sheet protection, or clear
    protection entirely. Excel enforces this in its UI; openpyxl (ProSE) writes
    through it regardless, so scans keep refreshing the locked column.

    Structural ops (insert/delete rows & columns) stay blocked, but the things a
    reviewer actually uses — selecting cells, sorting, AutoFilter, formatting —
    are explicitly allowed so the collaborator's workflow isn't hindered. No
    password: this guards against *accidental* edits; Review > Unprotect Sheet
    removes it if ever needed.
    """
    if not protect_id:
        ws.protection = SheetProtection(sheet=False)
        return
    ws.protection = SheetProtection(
        sheet=True,
        selectLockedCells=False, selectUnlockedCells=False,   # allow selecting/copying
        sort=False, autoFilter=False,                         # allow sort + filter
        formatCells=False, formatColumns=False, formatRows=False,  # allow formatting
        insertRows=True, insertColumns=True, insertHyperlinks=True,
        deleteRows=True, deleteColumns=True, pivotTables=True,
        objects=False, scenarios=False,
    )


def _style_header(ws, border=BORDER, protect_id=False) -> None:
    for col in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col, value=HEADERS[col - 1])
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = border
        if protect_id:
            cell.protection = LOCKED  # headers aren't editable when protected
        # Only seed the default width for columns that have no dimension yet (a
        # fresh sheet, or the newly-added Keyword column). Any column already in
        # column_dimensions keeps its width, preserving the user's adjustments.
        # Note: check membership BEFORE indexing -- ws.column_dimensions[letter]
        # auto-creates an entry, which would defeat the test.
        letter = get_column_letter(col)
        if letter not in ws.column_dimensions:
            ws.column_dimensions[letter].width = COLUMN_WIDTHS.get(col, 16)
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"


def _style_data_cell(cell, col: int, banded: bool, expired: bool = False, border=BORDER,
                     protect_id: bool = False) -> None:
    cell.font = EXPIRED_FONT if expired else DATA_FONT
    cell.border = border
    if protect_id:
        # Lock only the Solicitation # column; everything else stays editable.
        cell.protection = LOCKED if col == SOLICITATION_COL else UNLOCKED
    # Title left-wraps; short data/manual columns are centered for a clean look.
    # Phone (12) centers but wraps, so a dual-contact multi-line value shows both.
    if col in (3, 4, 11, 13, 14):
        cell.alignment = LEFT_WRAP
    elif col == 12:
        cell.alignment = CENTER_WRAP
    else:
        cell.alignment = CENTER
    if banded:
        cell.fill = BAND_FILL


def _new_workbook(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET_TITLE
    _style_header(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return wb


def _read_rows(ws) -> list[dict]:
    """Read existing data rows into a list of {col_index: value} dicts."""
    rows = []
    for r in range(2, ws.max_row + 1):
        record = {c: ws.cell(row=r, column=c).value for c in range(1, len(HEADERS) + 1)}
        # Skip completely empty rows.
        if all(v in (None, "") for v in record.values()):
            continue
        rows.append(record)
    return rows


def update_spreadsheet(path, details: list[dict], skip_on_lock: bool = False,
                       protect_id: bool = False) -> dict:
    """Merge scanned ``details`` into the workbook at ``path``.

    Returns {"new": int, "updated": int, "total_rows": int, ...}.

    ``skip_on_lock`` controls what happens when the file is locked (open in
    Excel / held by a co-author): when False (local use) the merge is saved to a
    timestamped sibling so results aren't lost; when True (a shared
    SharePoint/OneDrive workbook) the write is SKIPPED instead — no sibling is
    dropped into the shared library, and the next scheduled scan merges once the
    file is closed. Scans re-query the source every run, so nothing is lost
    permanently either way.

    ``protect_id`` locks the Solicitation # column (via Excel sheet protection)
    so a collaborator can't accidentally edit the key ProSE matches rows on;
    every other column stays editable. Re-applied every run.
    """
    path = Path(path)
    if path.exists():
        wb = openpyxl.load_workbook(path)
        ws = wb.active
    else:
        wb = _new_workbook(path)
        ws = wb.active

    existing = _read_rows(ws)
    # Capture the border the user has applied before we wipe the data area, so
    # the rewrite preserves it (falls back to the default on a fresh sheet).
    data_border = _detect_border(ws) or BORDER

    # Index existing rows by solicitation # (normalised). Rows without a
    # solicitation # are carried through untouched at the end.
    by_key: dict[str, dict] = {}
    carry: list[dict] = []
    order: list[str] = []
    for rec in existing:
        key = str(rec.get(SOLICITATION_COL) or "").strip()
        if key:
            if key not in by_key:      # hand-added duplicate rows: keep the first
                order.append(key)
            by_key.setdefault(key, rec)
        else:
            carry.append(rec)

    new_count = 0
    updated_count = 0
    new_keys: list[str] = []

    def published_sort_key(detail: dict):
        # newest first; expects MM/DD/YYYY, falls back to string
        val = detail.get("published") or ""
        parts = val.split("/")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            mm, dd, yy = parts
            return (int(yy), int(mm), int(dd))
        return (0, 0, 0)

    for detail in sorted(details, key=published_sort_key):  # ascending; prepended -> newest ends on top
        key = str(detail.get("solicitation_number") or "").strip()
        if not key:
            continue
        if key in by_key:
            rec = by_key[key]
            for field, col in FIELD_TO_COL.items():
                rec[col] = detail.get(field, "")
            updated_count += 1
        else:
            rec = {c: "" for c in range(1, len(HEADERS) + 1)}
            for field, col in FIELD_TO_COL.items():
                rec[col] = detail.get(field, "")
            by_key[key] = rec
            new_keys.append(key)
            new_count += 1

    # Final order: newest new-keys on top (new_keys is oldest->newest, so reverse),
    # then previously-existing rows in their prior order, then carry rows.
    final_order = list(reversed(new_keys)) + [k for k in order if k not in new_keys]
    ordered_records = [by_key[k] for k in final_order] + carry

    # Sink expired solicitations (past their due date) to the bottom, preserving
    # the relative order within each group. Recomputed every run against "now".
    now = datetime.now()
    active = [rec for rec in ordered_records if not _is_expired(rec.get(DUE_COL), now)]
    expired = [rec for rec in ordered_records if _is_expired(rec.get(DUE_COL), now)]
    ordered_records = active + expired
    first_expired = len(active)  # rows at this index and below are struck through

    # Wipe existing data area (values + styles) then rewrite.
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row - 1)

    for i, rec in enumerate(ordered_records):
        row = i + 2
        banded = (i % 2 == 1)
        is_expired = i >= first_expired
        for col in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=row, column=col, value=rec.get(col))
            _style_data_cell(cell, col, banded, is_expired, data_border, protect_id)

    # Re-assert header styling (cheap, keeps look consistent).
    _style_header(ws, data_border, protect_id)
    # Lock the Solicitation # column (or clear protection) every run.
    _apply_protection(ws, protect_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    saved_to = path
    try:
        wb.save(path)
    except PermissionError:
        # The workbook is open in Excel / held by a co-author (Windows locks it).
        if skip_on_lock:
            # Shared library: skip this run rather than littering a conflicting
            # sibling into the synced folder. The next scan will merge.
            return {
                "new": 0,
                "updated": 0,
                "total_rows": len(ordered_records),
                "saved_to": str(path),
                "diverted": False,
                "skipped_locked": True,
            }
        # Local use: don't lose the scan — save to a timestamped sibling.
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        saved_to = path.with_name(f"{path.stem} (scan {stamp}){path.suffix}")
        wb.save(saved_to)

    return {
        "new": new_count,
        "updated": updated_count,
        "total_rows": len(ordered_records),
        "saved_to": str(saved_to),
        "diverted": saved_to != path,
        "skipped_locked": False,
    }
