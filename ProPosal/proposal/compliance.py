"""Practical compliance checklist (flag-only).

Verifies the concrete, checkable rules of a City & County submittal: required
sections present, selected categories within the allowed set, exported-PDF size
under the cap, page count within the limit. WARN means we couldn't verify (e.g.
no PDF exported yet); FAIL is a hard violation. Never edits the document.

The deeper "validate against the annual notice PDF" pass is Phase 5; this
checklist works offline from the store and the document itself.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.document import Document as _DocClass

from . import docx_map, pdfutil
from .checks import ChecklistReport
from .docx_edit import para_text


def _as_doc(doc_or_path):
    return doc_or_path if isinstance(doc_or_path, _DocClass) else Document(str(doc_or_path))


def _has_cover_letter(doc) -> bool:
    if docx_map.find_cover_date_paragraphs(doc):
        return True
    return any("dear" in para_text(p).strip().lower()[:6] for p in doc.paragraphs)


def run_checklist(doc_or_path, store: dict | None = None, cfg: dict | None = None,
                  *, pdf_path=None) -> ChecklistReport:
    store = store or {}
    cfg = cfg or {}
    opp = store.get("opportunity", {})
    doc = _as_doc(doc_or_path)
    rep = ChecklistReport("Compliance checklist")

    # 1. Required sections present
    missing = docx_map.missing_headings(doc)
    if not _has_cover_letter(doc):
        missing = ["Cover letter"] + missing
    if missing:
        rep.fail("Required sections present", f"missing: {', '.join(missing)}")
    else:
        rep.pass_("Required sections present", "all 6 sections + cover letter")

    # 2. Selected categories within the allowed set. Only an explicit
    # `opportunity.allowed_categories` is authoritative -- the store's
    # `categories` list is *descriptive* (often partial), so using it as the
    # allowed set false-fails valid stores. Without an explicit set we can't
    # verify offline: WARN and point at the notice validation.
    selected = [str(c) for c in opp.get("selected_categories", [])]
    allowed = [str(c) for c in opp.get("allowed_categories", [])]
    if not selected:
        rep.warn("Categories within allowed set", "no selected_categories in store")
    elif not allowed:
        rep.warn("Categories within allowed set",
                 "no allowed_categories in store; verify with 'Validate vs notice' (4a)")
    else:
        bad = [c for c in selected if c not in allowed]
        if bad:
            rep.fail("Categories within allowed set", f"not allowed: {', '.join(bad)}")
        else:
            rep.pass_("Categories within allowed set", f"{len(selected)} selected")
    # Soft consistency: selections with no matching description in Section I.
    described = {str(c.get("dit_number")) for c in store.get("categories", [])
                 if c.get("dit_number")}
    undescribed = [c for c in selected if described and c not in described]
    if undescribed:
        rep.warn("Selected categories described in store",
                 f"no `categories` entry for: {', '.join(undescribed)}")

    # 3 & 4. PDF size + page count (need an exported PDF)
    pdf = Path(pdf_path) if pdf_path else None
    if pdf is None and isinstance(doc_or_path, (str, Path)):
        pdf = pdfutil.find_companion_pdf(doc_or_path)
    cap = float(cfg.get("pdf_size_cap_mb", 3.0))
    limit = int(cfg.get("page_limit", 30))

    if pdf and pdf.exists():
        size = pdfutil.pdf_size_mb(pdf)
        if size <= cap:
            rep.pass_("PDF size under cap", f"{size:.2f} MB <= {cap} MB")
        else:
            rep.fail("PDF size under cap", f"{size:.2f} MB > {cap} MB")
        pages = pdfutil.pdf_page_count(pdf)
        if pages is None:
            rep.warn("Page limit", "could not read page count")
        elif pages <= limit:
            rep.pass_("Page limit", f"{pages} <= {limit} pages")
        else:
            rep.fail("Page limit", f"{pages} > {limit} pages")
    else:
        rep.warn("PDF size under cap", "export the submittal to PDF from Word to verify")
        rep.warn("Page limit", "export the submittal to PDF from Word to verify")

    # 5. Deliverable format
    required_form = opp.get("required_form", "general")
    if required_form and required_form.lower() != "general":
        rep.warn("Required form", f"this department wants '{required_form}'; not yet generated")
    else:
        rep.pass_("Required form", "general DIT docx format")

    return rep
