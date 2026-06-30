"""Parse the City & County annual notice (ad) PDF and validate against it.

This is the optional, manually-run "validate against requirements" pass. The
notice states, on page 1, the fiscal year, the submittal email, the deadline,
and the attachment/email size caps; each department section then lists its
service categories and (for some) the required form (e.g. Modified SF330).

Parsing a 22-page government PDF is inherently heuristic, so everything here is
FLAG-ONLY and clearly worded -- it never edits a document and never blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .checks import ChecklistReport

# Map a store department code -> a keyword found in the notice's heading.
DEPT_KEYWORDS = {
    "DIT": "INFORMATION TECHNOL",      # notice OCR reads 'TECHNOLOCY'
    "DDC": "DESIGN AND CONSTRUCTION",
    "CORP": "CORPORATION COUN",
    "DPR": "PARKS AND RECREATION",
    "PROS": "PROSECUTING",
    "DTS": "TRANSPORTATION SERVICES",
}


@dataclass
class Department:
    name: str
    categories: list[dict] = field(default_factory=list)  # {marker, text}
    required_form: str = "general"                          # general | SF330 | DPW-120
    block: str = ""


@dataclass
class NoticeInfo:
    fiscal_year: int | None = None
    submittal_email: str = ""
    deadline: str = ""
    contract_period: str = ""
    pdf_size_cap_mb: float | None = None
    email_cap_mb: float | None = None
    departments: list[Department] = field(default_factory=list)
    error: str | None = None


_HEADING_RE = re.compile(
    r"(?:[A-Z]\.\s+)?DEPARTMENT OF (?:THE )?[A-Z][A-Z .&/()'-]{3,}", re.MULTILINE
)


def _form_for(block: str) -> str:
    if re.search(r"DPW-?120", block, re.IGNORECASE):
        return "DPW-120"
    if re.search(r"(modified )?standard form 330|SF[- ]?330|form 330", block, re.IGNORECASE):
        return "SF330"
    return "general"


def _categories_in(block: str) -> list[dict]:
    """Lettered sub-items ('a. ...') and numbered GS rows ('1. GS-1550 ...')."""
    cats = []
    for m in re.finditer(r"(?m)^\s*([a-z])\.\s+(.{3,120})", block):
        cats.append({"marker": m.group(1), "text": m.group(2).strip()})
    if not cats:
        for m in re.finditer(r"(?m)^\s*(\d+)\.\s+(GS-?\d+[^\n]{0,100})", block):
            cats.append({"marker": m.group(1), "text": m.group(2).strip()})
    return cats


def parse_notice(pdf_path) -> NoticeInfo:
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
    except Exception as exc:  # noqa: BLE001
        return NoticeInfo(error=f"Could not read notice PDF: {exc}")

    full = "\n".join(pages)
    info = NoticeInfo()

    m = re.search(r"Fiscal Year\s*(20\d\d)", full, re.IGNORECASE)
    info.fiscal_year = int(m.group(1)) if m else None
    m = re.search(r"[\w.\-]+@honolulu\.gov", full)
    info.submittal_email = m.group(0) if m else ""
    m = re.search(r"No later than.{0,60}?on\s+([A-Z][a-z]+ \d{1,2},?\s*20\d\d)", full)
    info.deadline = m.group(1).strip() if m else ""
    m = re.search(r"period of\s+([A-Z][a-z]+ \d{1,2},?\s*20\d\d\s*to\s*[A-Z][a-z]+ \d{1,2},?\s*20\d\d)", full)
    info.contract_period = m.group(1).strip() if m else ""
    m = re.search(r"(\d+\.?\d*)\s*MB per attachment", full, re.IGNORECASE)
    info.pdf_size_cap_mb = float(m.group(1)) if m else None
    m = re.search(r"not exceed\s*(\d+)\s*MB", full, re.IGNORECASE)
    info.email_cap_mb = float(m.group(1)) if m else None

    # Department sections: slice between consecutive headings.
    heads = list(_HEADING_RE.finditer(full))
    for i, h in enumerate(heads):
        start = h.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(full)
        block = full[start:end]
        name = re.sub(r"^[A-Z]\.\s+", "", re.sub(r"\s+", " ", h.group(0)).strip())
        info.departments.append(
            Department(name=name, categories=_categories_in(block),
                       required_form=_form_for(block), block=block)
        )
    return info


_STOP_WORDS = {"DEPARTMENT", "OFFICE", "THE", "AND", "FOR", "SERVICES"}


def find_department(notice: NoticeInfo, dept_code: str, dept_full: str = "") -> Department | None:
    # 1) the department-code keyword, checked across ALL departments first
    kw = DEPT_KEYWORDS.get((dept_code or "").upper(), "")
    if kw:
        for d in notice.departments:
            if kw in d.name.upper():
                return d
    # 2) fall back to distinctive words from the full name (skip common ones)
    words = [w for w in dept_full.upper().split() if len(w) > 4 and w not in _STOP_WORDS]
    for d in notice.departments:
        up = d.name.upper()
        if any(w in up for w in words):
            return d
    return None


def _marker_for_selected(sel: str, dept: Department) -> str:
    """A DIT '#' maps to a lettered sub-item (1->a); else it stays numeric."""
    markers = {c["marker"] for c in dept.categories}
    if markers and all(mk.isalpha() for mk in markers):
        try:
            n = int(sel)
            return chr(ord("a") + n - 1) if 1 <= n <= 26 else f"#{sel}"
        except ValueError:
            return sel
    return sel


def validate(notice: NoticeInfo, store: dict, target_fy: int | None = None) -> ChecklistReport:
    rep = ChecklistReport("Validation vs. the City notice")
    if notice.error:
        rep.fail("Read notice PDF", notice.error)
        return rep
    opp = store.get("opportunity", {})

    # 1. Fiscal year
    want_fy = target_fy or opp.get("fiscal_year")
    if notice.fiscal_year is None:
        rep.warn("Fiscal year", "couldn't read the fiscal year from the notice")
    elif want_fy and int(want_fy) != notice.fiscal_year:
        rep.fail("Fiscal year",
                 f"notice is for FY{notice.fiscal_year}; your submittal targets FY{want_fy}")
    else:
        rep.pass_("Fiscal year", f"notice FY{notice.fiscal_year}"
                  + (f" matches FY{want_fy}" if want_fy else ""))

    # 2. Deadline + caps (informational)
    if notice.deadline:
        rep.warn("Submittal deadline", f"{notice.deadline} (4:30 p.m. HST) -- verify it hasn't passed")
    if notice.pdf_size_cap_mb:
        rep.pass_("Attachment size cap", f"notice: {notice.pdf_size_cap_mb} MB per attachment")
    if notice.submittal_email:
        rep.pass_("Submittal email", notice.submittal_email)

    # 3. Department + categories
    dept = find_department(notice, opp.get("department", ""), opp.get("department_full", ""))
    if dept is None:
        rep.warn("Department categories", "couldn't locate your department's section in the notice")
        return rep

    # required form
    want_form = (opp.get("required_form") or "general").lower()
    if dept.required_form != "general" and want_form == "general":
        rep.fail("Required form",
                 f"notice requires {dept.required_form} for {dept.name}; your store says 'general'")
    else:
        rep.pass_("Required form", f"{dept.name}: {dept.required_form}")

    # selected categories within the department's listed items
    selected = [str(c) for c in opp.get("selected_categories", [])]
    if not selected:
        rep.warn("Selected categories", "no selected_categories in the store")
    elif not dept.categories:
        rep.warn("Selected categories",
                 f"couldn't parse category items for {dept.name} (got {len(dept.categories)})")
    else:
        markers = {c["marker"] for c in dept.categories}
        bad = [s for s in selected if _marker_for_selected(s, dept) not in markers]
        if bad:
            rep.fail("Selected categories",
                     f"notice lists {len(markers)} item(s) for {dept.name}; "
                     f"these selections aren't in it: {', '.join(bad)}")
        else:
            rep.pass_("Selected categories",
                      f"all {len(selected)} within {dept.name}'s {len(markers)} listed item(s)")
    return rep


def find_notice_pdf(folder) -> Path | None:
    """A PDF in ``folder`` that looks like the annual notice/ad."""
    d = Path(folder)
    if not d.is_dir():
        return None
    for p in d.rglob("*.pdf"):
        n = p.name.lower()
        if any(k in n for k in ("annual", "fiscal year", "fiscalyear", "notice", "ad-fiscal")):
            return p
    return None
