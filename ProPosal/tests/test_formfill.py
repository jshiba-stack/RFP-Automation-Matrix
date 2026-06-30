"""Tests for the PDF form-fill engine (DPW-120 AcroForm)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import formfill, forms  # noqa: E402

DPW120 = ROOT / "assets/refs/DPW-120-fillable.pdf"
SF330 = ROOT / "assets/refs/Modified-SF330_Qualification_Form.pdf"
pytestmark = pytest.mark.skipif(not DPW120.exists(), reason="DPW-120 template not available")

STORE = {
    "firm": {
        "legal_name": "Acme Consulting Group",
        "address_lines": ["123 Example Ave, Suite 100", "Honolulu, HI 96800"],
        "signatory": {"name": "Jordan Avery"},
    }
}


def test_dpw120_is_fillable():
    assert len(formfill.field_names(DPW120)) > 100


def test_fill_from_store(tmp_path):
    pdf, report = formfill.fill(DPW120, forms.DPW120_MAP, STORE)
    assert pdf is not None
    out = tmp_path / "filled.pdf"
    out.write_bytes(pdf)
    vals = formfill.read_fields(out)
    assert vals["FIRM NAME"] == "Acme Consulting Group"
    assert "Honolulu, HI 96800" in vals["BUSINESS ADDRESS TELEPHONE  FAX NO OF HAWAII OFFICE"]
    assert vals["PRINCIPALS OF FIRM NAMES"] == "Jordan Avery"
    # the many unmapped fields are flagged, not silently dropped
    assert any("left blank" in f.summary for f in report.flags)


@pytest.mark.skipif(not SF330.exists(), reason="SF330 template not available")
def test_flat_sf330_is_flagged_not_filled():
    pdf, report = formfill.fill(SF330, {}, STORE)
    assert pdf is None
    assert any("no fillable fields" in f.summary.lower() for f in report.flags)


def test_carry_forward_from_previous(tmp_path):
    # 1) make a "previous" filled form
    prev_bytes, _ = formfill.fill(DPW120, forms.DPW120_MAP, STORE)
    prev = tmp_path / "prev.pdf"
    prev.write_bytes(prev_bytes)

    # 2) fill a fresh template with an EMPTY store but carry the previous values
    pdf, report = formfill.fill(DPW120, {}, {}, prev_filled=prev)
    out = tmp_path / "new.pdf"
    out.write_bytes(pdf)
    vals = formfill.read_fields(out)
    assert vals["FIRM NAME"] == "Acme Consulting Group"     # carried over by field name
    assert any("carried" in r.summary for r in report.applied_records)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
