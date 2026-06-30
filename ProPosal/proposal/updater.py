"""PRIMARY mode: smart copy-and-update of a previous FINAL submittal.

Opens last year's FINAL .docx, auto-applies the handful of mechanical edits, and
flags everything else. The base file is never mutated -- we save a new draft.

Auto-applied (each still reported):
  * Fiscal year bump  -- 'Fiscal Year 2026' / 'for the fiscal year 2026' / footer 'FY26'
  * Cover + letter date -> the build date
  * Ongoing Capacity end-dates ('2025+') -> '<as-of-year>+'

Flagged (never silently changed):
  * A match whose runs have mixed formatting (UNSAFE EDIT)
  * The Capacity table missing (MISSING)
  * Store projects / past-performance with no home in the base (ADD MANUALLY)
"""

from __future__ import annotations

import datetime as _dt
import re

from docx import Document

from . import docx_map
from .docx_edit import para_text, replace_in_paragraph
from .flags import KIND_ADD, KIND_MISSING, KIND_UNSAFE, Report


def _coerce_date(value, fallback: _dt.date) -> _dt.date:
    if value in (None, ""):
        return fallback
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    s = str(value).strip()
    # ISO 'YYYY-MM-DD'
    try:
        return _dt.date.fromisoformat(s)
    except ValueError:
        pass
    # 'Month D, YYYY'
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized cover_date: {value!r}")


def _fmt_date(d: _dt.date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def build(
    base_path,
    store: dict | None = None,
    *,
    target_fy: int | None = None,
    cover_date=None,
    today: _dt.date | None = None,
    resumes_dir=None,
    log=print,
):
    """Return ``(Document, Report)``. Caller saves the document."""
    store = store or {}
    opp = store.get("opportunity", {})
    today = today or _dt.date.today()

    doc = Document(str(base_path))
    report = Report(base=str(base_path))

    detected_fy = docx_map.detect_fiscal_year(doc)
    if target_fy is None:
        target_fy = opp.get("fiscal_year") or ((detected_fy + 1) if detected_fy else None)
    if target_fy is None:
        report.flag("document", "Could not detect a fiscal year to bump.", KIND_MISSING)

    cover = _coerce_date(cover_date if cover_date is not None else opp.get("cover_date"), today)
    as_of_year = cover.year

    log(f"Detected FY {detected_fy} -> target FY {target_fy}; cover date {_fmt_date(cover)}")

    if target_fy:
        apply_fiscal_year(doc, target_fy, report)
    apply_cover_dates(doc, cover, report)
    apply_ongoing_end_dates(doc, as_of_year, report)
    _flag_new_entities(doc, store, report)
    if resumes_dir:
        from . import resumes
        resumes.add_resume_flags(report, store, resumes_dir)

    return doc, report


# --- reusable scalar edits (shared with generate mode) ---------------------

def apply_fiscal_year(doc, target_fy: int, report: Report) -> None:
    """Bump every fiscal-year reference: title, inline letter text, footer FY##."""
    for p, kind in docx_map.find_fiscal_year_paragraphs(doc):
        if kind == "fiscal_year":
            res = replace_in_paragraph(p, r"Fiscal Year 20\d\d", f"Fiscal Year {target_fy}")
        else:  # inline 'for the fiscal year YYYY'
            res = replace_in_paragraph(
                p, r"(?<=fiscal year )20\d\d", str(target_fy), flags=re.IGNORECASE
            )
        _record(report, "Fiscal year", res)

    fy2 = f"FY{target_fy % 100:02d}"  # surgical: leaves the footer PAGE field intact
    for p, si in docx_map.footer_paragraphs(doc):
        if docx_map.RE_FOOTER_FY.search(para_text(p)):
            res = replace_in_paragraph(p, r"FY\d{2}", fy2)
            _record(report, f"Footer (section {si})", res)


def apply_cover_dates(doc, cover: _dt.date, report: Report) -> None:
    new_date = _fmt_date(cover)
    date_paras = docx_map.find_cover_date_paragraphs(doc)
    if not date_paras:
        report.flag("cover", "No cover/letter date paragraph found.", KIND_MISSING)
    for p, label in date_paras:
        res = replace_in_paragraph(p, docx_map.RE_FULL_DATE, new_date)
        _record(report, label, res)


def apply_ongoing_end_dates(doc, as_of_year: int, report: Report) -> None:
    """Refresh ongoing Capacity end-dates ('2025+') to '<as_of_year>+'."""
    tbl = docx_map.find_capacity_table(doc)
    if tbl is None:
        report.flag(
            "Capacity",
            "Capacity table not found (header Client/Project/Start Date/End Date).",
            KIND_MISSING,
        )
        return
    header = [c.text.strip().lower() for c in tbl.rows[0].cells]
    try:
        end_col = header.index("end date")
    except ValueError:
        end_col = len(header) - 1
    for ri, row in enumerate(tbl.rows[1:], start=1):
        cell = row.cells[end_col]
        for para in cell.paragraphs:
            if docx_map.RE_ONGOING_YEAR.search(para_text(para)):
                res = replace_in_paragraph(para, docx_map.RE_ONGOING_YEAR, str(as_of_year))
                _record(report, f"Capacity r{ri} End Date", res, what="ongoing end-date")


def _record(report: Report, location: str, res, what: str = "value") -> None:
    if not res.matched:
        return
    if res.applied:
        report.applied(location, f"updated {what}", res.old, res.new)
    elif not res.rpr_uniform:
        report.flag(
            location,
            f"{what} spans mixed formatting; left unchanged -- edit by hand.",
            KIND_UNSAFE,
            res.old,
            res.new,
        )


def _flag_new_entities(doc, store: dict, report: Report) -> None:
    # Past-performance clients present in the store but absent from the doc.
    doc_clients = {
        c.strip().lower().replace("\n", " ")
        for c in docx_map.find_past_performance_clients(doc)
    }
    for pp in store.get("past_performance", []):
        name = str(pp.get("client", "")).strip()
        if name and name.lower().replace("\n", " ") not in doc_clients:
            report.flag(
                "Past Performance",
                f"Store has a client not in the base doc: add a block manually.",
                KIND_ADD,
                new=name,
            )

    # Projects in the store with no matching Capacity row.
    tbl = docx_map.find_capacity_table(doc)
    if tbl is not None and store.get("projects"):
        rows = set()
        for row in tbl.rows[1:]:
            client = row.cells[0].text.strip().lower()
            project = row.cells[1].text.strip().lower()
            rows.add((client, project))
        for proj in store["projects"]:
            key = (str(proj.get("client", "")).strip().lower(),
                   str(proj.get("project", "")).strip().lower())
            if key not in rows:
                report.flag(
                    "Capacity",
                    "Store has a project not in the base Capacity table: add a row manually.",
                    KIND_ADD,
                    new=f"{proj.get('client','')} / {proj.get('project','')}",
                )
