"""Read/update the styled Excel workbook.

Design goals (from the spec):
  * 13 columns, fixed left-to-right order.
  * The program only ever fills the 8 DATA columns; the 5 MANUAL columns
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

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

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
]

SOLICITATION_COL = 2  # column B holds the dedupe key

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
}

COLUMN_WIDTHS = {
    1: 12, 2: 16, 3: 20, 4: 46, 5: 13, 6: 20,
    7: 10, 8: 10, 9: 12, 10: 12, 11: 20, 12: 16, 13: 28,
}

# --- styling palette --------------------------------------------------------
HEADER_FILL = PatternFill("solid", fgColor="1F4E5F")   # deep teal
BAND_FILL = PatternFill("solid", fgColor="EAF1F4")     # light teal banding
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
DATA_FONT = Font(name="Calibri", size=11, color="222222")
_THIN = Side(style="thin", color="BFC9CE")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=False)
SHEET_TITLE = "Scanned Professional Services"


def _style_header(ws) -> None:
    for col in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col, value=HEADERS[col - 1])
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(col)].width = COLUMN_WIDTHS.get(col, 16)
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"


def _style_data_cell(cell, col: int, banded: bool) -> None:
    cell.font = DATA_FONT
    cell.border = BORDER
    # Title left-wraps; short data/manual columns are centered for a clean look.
    if col in (3, 4, 11, 13):
        cell.alignment = LEFT_WRAP
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


def update_spreadsheet(path, details: list[dict]) -> dict:
    """Merge scanned ``details`` into the workbook at ``path``.

    Returns {"new": int, "updated": int, "total_rows": int}.
    """
    path = Path(path)
    if path.exists():
        wb = openpyxl.load_workbook(path)
        ws = wb.active
    else:
        wb = _new_workbook(path)
        ws = wb.active

    existing = _read_rows(ws)

    # Index existing rows by solicitation # (normalised). Rows without a
    # solicitation # are carried through untouched at the end.
    by_key: dict[str, dict] = {}
    carry: list[dict] = []
    order: list[str] = []
    for rec in existing:
        key = str(rec.get(SOLICITATION_COL) or "").strip()
        if key:
            by_key[key] = rec
            order.append(key)
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

    # Wipe existing data area (values + styles) then rewrite.
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row - 1)

    for i, rec in enumerate(ordered_records):
        row = i + 2
        banded = (i % 2 == 1)
        for col in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=row, column=col, value=rec.get(col))
            _style_data_cell(cell, col, banded)

    # Re-assert header styling (cheap, keeps look consistent).
    _style_header(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)

    return {
        "new": new_count,
        "updated": updated_count,
        "total_rows": len(ordered_records),
    }
