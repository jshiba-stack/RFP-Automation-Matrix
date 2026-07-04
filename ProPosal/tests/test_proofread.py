"""Unit tests for the table proofread pass + output-name sanitizer.

Synthetic python-docx fixtures only (fictional data -- public-repo rule):
  * a Section-II-shaped table with a few undersized rows -> normalized to the mode
  * two past-performance-shaped sibling tables, one missing its interior border
    -> the deficient one gains the border its sibling carries
  * _safe_stem sanitizes user-supplied output names
"""

import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from proposal import proofread  # noqa: E402
from proposal.flags import KIND_REVIEW, Report  # noqa: E402
from proposal.jobs import _safe_stem  # noqa: E402


def _silent(*_a, **_k):
    pass


def _sizes(table):
    return {run.font.size
            for row in table.rows[1:]
            for cell in row.cells
            for para in cell.paragraphs
            for run in para.runs}


def test_font_normalizes_undersized_rows_to_the_mode():
    doc = Document()
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "Resource"
    t.rows[0].cells[1].text = "Qualifications"
    # three rows at 11pt, one (the outlier) at 9pt
    for name, pt in [("Alex", 11), ("Blair", 11), ("Casey", 11), ("Rene", 9)]:
        row = t.add_row()
        for ci, text in enumerate((name, "quals")):
            run = row.cells[ci].paragraphs[0].add_run(text)
            run.font.size = Pt(pt)

    report = Report()
    proofread.proofread_document(doc, report, log=_silent)

    assert _sizes(t) == {Pt(11)}, "all data-row runs should be the dominant 11pt"
    assert any(r.status == "applied" and "font size" in r.summary
               for r in report.applied_records)
    assert any(r.is_flag and r.kind == KIND_REVIEW for r in report.flags)


def test_uniform_table_is_left_untouched():
    doc = Document()
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "Resource"
    t.rows[0].cells[1].text = "Qualifications"
    for name in ("Alex", "Blair"):
        row = t.add_row()
        row.cells[0].paragraphs[0].add_run(name).font.size = Pt(11)
        row.cells[1].paragraphs[0].add_run("quals").font.size = Pt(11)

    report = Report()
    out = proofread.proofread_document(doc, report, log=_silent)
    assert out["font_tables"] == 0
    assert not report.applied_records and not report.flags


def _mk_inside_h():
    el = OxmlElement("w:insideH")
    for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", "auto")):
        el.set(qn(f"w:{k}"), v)
    return el


def _pastperf(doc, client):
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "Client"
    t.rows[0].cells[1].text = client
    t.add_row().cells[0].text = "Detailed scope of work"
    t.add_row().cells[0].text = "Issue resolution"
    return t


def test_border_added_to_deficient_sibling():
    doc = Document()
    good = _pastperf(doc, "Acme")
    proofread._set_inside_h(good, _mk_inside_h())      # good has the border
    bad = _pastperf(doc, "Globex")                     # bad does not

    assert proofread._is_real_border(proofread._inside_h(good))
    assert not proofread._is_real_border(proofread._inside_h(bad))

    report = Report()
    out = proofread.proofread_document(doc, report, log=_silent)

    assert out["border_tables"] == 1
    assert proofread._is_real_border(proofread._inside_h(bad)), \
        "deficient sibling should gain the interior border"
    assert any(r.status == "applied" and "border" in r.summary for r in report.applied_records)
    assert any(r.is_flag and "border" in r.summary for r in report.flags)


def test_safe_stem_sanitizes():
    assert _safe_stem("My Submittal.docx") == "My Submittal"
    assert _safe_stem('  "Acme FY26"  ') == "Acme FY26"
    assert _safe_stem("a/b:c*?.pdf") == "abc"          # ext stripped, illegal removed
    assert _safe_stem("") is None
    assert _safe_stem("   ") is None
    assert _safe_stem("***") is None                   # nothing usable left
