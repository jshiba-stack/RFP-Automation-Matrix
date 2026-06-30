"""Integration tests for the smart copy-and-update engine against the real FINAL.

The FY2026 FINAL + FY2027 deltas are the ground-truth acceptance target:
bumping it must change exactly the fiscal year (title + inline + footer), both
cover dates, and the ongoing Capacity end-dates -- nothing else.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import updater  # noqa: E402
from proposal.docx_edit import iter_all_paragraphs, para_text  # noqa: E402

BASE = next(iter(sorted((ROOT / "assets/refs").glob("*FINAL*.docx"))), ROOT / "assets/refs/__none__.docx")

pytestmark = pytest.mark.skipif(not BASE.exists(), reason="reference FINAL not available")


def _all_texts(doc):
    out = [para_text(p) for p in iter_all_paragraphs(doc)]
    for sec in doc.sections:
        for p in sec.footer.paragraphs:
            t = para_text(p)
            if t.strip():
                out.append("FOOTER: " + t)
    return out


def test_acceptance_exactly_ten_intended_changes():
    from docx import Document

    base_texts = _all_texts(Document(str(BASE)))
    doc, report = updater.build(BASE, {}, target_fy=2027, cover_date="2026-03-02")
    out_texts = _all_texts(doc)

    assert len(base_texts) == len(out_texts)
    changed = [(a, b) for a, b in zip(base_texts, out_texts) if a != b]
    assert len(changed) == 10, changed
    assert report.flags == []
    assert len(report.applied_records) == 10

    # the specific edits
    joined = "\n".join(out_texts)
    assert "Fiscal Year 2027" in joined
    assert "for the fiscal year 2027" in joined
    assert "March 2, 2026" in joined
    assert "FY27 Professional Services Submittal" in joined
    assert joined.count("2026+") == 5          # ongoing rows refreshed
    assert "2024" in joined and "2023" in joined  # completed years untouched
    assert "2025+" not in joined


def test_ongoing_uses_cover_date_year():
    doc, _ = updater.build(BASE, {}, target_fy=2028, cover_date="2027-01-15")
    texts = "\n".join(_all_texts(doc))
    assert "2027+" in texts and "2025+" not in texts


def test_new_store_project_is_flagged_add_manually():
    store = {
        "projects": [
            {"id": "x", "client": "Brand New Client LLC", "project": "Net-New Thing", "end": "ongoing"}
        ]
    }
    _, report = updater.build(BASE, store, target_fy=2027, cover_date="2026-03-02")
    add_flags = [f for f in report.flags if f.kind == "ADD MANUALLY"]
    assert any("Brand New Client" in f.new for f in add_flags)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
