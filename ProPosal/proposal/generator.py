"""SECONDARY mode: generate a submittal from a template + the data store.

The template carries the static prose, logo, header/footer, page numbering, and
named styles (by default last year's FINAL is a perfectly good template). The
data store drives the scalars (fiscal year, dates) and the data-driven tables.

Phase 2 rebuilds the two clean tabular sections directly mapped from the store:
  * Capacity / Project Listing  (Client / Project / Start Date / End Date)
  * Professional Qualifications (Resource / Qualifications)
Categories and Past Performance are kept from the template (their cells carry
rich multi-paragraph formatting); they remain a future enhancement and are
reported as template-sourced. Resumes listed in the store are appended when the
files resolve, else flagged.
"""

from __future__ import annotations

import datetime as _dt

from docx import Document

from . import docx_map, updater
from .docx_edit import rebuild_table_body
from .flags import KIND_ADD, KIND_MISSING, Report


def _end_str(project: dict, as_of_year: int) -> str:
    end = project.get("end")
    if end in (None, "", "ongoing"):
        return f"{as_of_year}+"
    return str(end)


def generate(
    template_path,
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

    doc = Document(str(template_path))
    report = Report(base=str(template_path))

    detected_fy = docx_map.detect_fiscal_year(doc)
    if target_fy is None:
        target_fy = opp.get("fiscal_year") or ((detected_fy + 1) if detected_fy else None)
    cover = updater._coerce_date(
        cover_date if cover_date is not None else opp.get("cover_date"), today
    )
    as_of_year = cover.year
    log(f"Generating from template; FY {target_fy}; cover date {updater._fmt_date(cover)}")

    # --- scalars (shared with primary mode) ---
    if target_fy:
        updater.apply_fiscal_year(doc, target_fy, report)
    updater.apply_cover_dates(doc, cover, report)

    # --- Capacity / Project Listing from store.projects ---
    projects = store.get("projects", [])
    cap = docx_map.find_capacity_table(doc)
    if cap is None:
        report.flag("Capacity", "Capacity table not found in template.", KIND_MISSING)
    elif projects:
        rows = [
            [
                str(p.get("client", "")),
                str(p.get("project", "")),
                str(p.get("start_year", "")),
                _end_str(p, as_of_year),
            ]
            for p in projects
        ]
        n = rebuild_table_body(cap, rows)
        report.applied("Capacity", f"rebuilt project listing from store ({n} rows)")
    else:
        report.flag("Capacity", "No projects in store; kept template rows.", KIND_ADD)

    # --- Professional Qualifications from store.personnel ---
    personnel = store.get("personnel", [])
    quals = docx_map.find_table_by_signature(doc, docx_map.SIG_QUALIFICATIONS)
    if not quals:
        report.flag("Qualifications", "Qualifications table not found in template.", KIND_MISSING)
    elif personnel:
        rows = [
            [str(p.get("name", "")), str(p.get("qualifications") or p.get("role", ""))]
            for p in personnel
        ]
        n = rebuild_table_body(quals[0], rows)
        report.applied("Qualifications", f"rebuilt resource table from store ({n} rows)")
    else:
        report.flag("Qualifications", "No personnel in store; kept template rows.", KIND_ADD)

    # --- Resumes (appendix) from the attached resumes folder ---
    _append_resumes(doc, store, resumes_dir, report)

    # --- Sections kept from the template (not yet store-driven) ---
    for section in ("Categories", "Past Performance", "Additional Criteria"):
        report.applied(section, "kept from template (not yet store-driven)")

    return doc, report


def _append_resumes(doc, store: dict, resumes_dir, report: Report) -> None:
    """Append matched .docx resumes from the folder; cross-verify the rest."""
    from . import resumes as resumes_mod

    personnel = store.get("personnel", [])
    if not personnel:
        return
    if not resumes_dir:
        report.flag("Resumes", "No resumes folder attached; resumes not appended.", KIND_ADD)
        return

    res = resumes_mod.add_resume_flags(report, store, resumes_dir)  # flags missing + orphans
    try:
        from docxcompose.composer import Composer
        composer = Composer(doc)
    except Exception:  # pragma: no cover
        composer = None
    for name, path in res["matched"]:
        if path.suffix.lower() == ".docx" and composer is not None:
            try:
                composer.append(Document(str(path)))
                report.applied("Appendix", f"appended resume: {name}")
            except Exception as exc:  # noqa: BLE001 - corrupt/locked file; don't crash
                report.flag("Appendix",
                            f"could not append {name}'s resume ({path.name}): {exc}",
                            KIND_ADD, new=path.name)
        else:
            report.flag("Appendix",
                        f"resume for {name} is {path.suffix} ({path.name}); add/convert it manually.",
                        KIND_ADD, new=path.name)
