"""Tests for parsing + validating against the City annual notice PDF."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import notice  # noqa: E402
from proposal.checks import FAIL, PASS, WARN  # noqa: E402

AD = ROOT / "assets/defaults/Professional-Services-Annual-Ad-Fiscal-Year-2026.pdf"
pytestmark = pytest.mark.skipif(not AD.exists(), reason="annual notice PDF not available")


@pytest.fixture(scope="module")
def info():
    return notice.parse_notice(str(AD))


def _status(rep, substr):
    for c in rep.checks:
        if substr.lower() in c.name.lower():
            return c.status
    return None


def test_parse_global_fields(info):
    assert info.error is None
    assert info.fiscal_year == 2026
    assert info.submittal_email.endswith("@honolulu.gov")
    assert info.pdf_size_cap_mb == 3.0
    assert info.email_cap_mb == 20.0
    assert "May 30, 2025" in info.deadline


def test_parse_departments_and_required_form(info):
    names = " | ".join(d.name for d in info.departments)
    assert "DESIGN AND CONSTRUCTION" in names
    assert "INFORMATION TECHNOL" in names
    ddc = next(d for d in info.departments if "DESIGN AND CONSTRUCTION" in d.name)
    assert ddc.required_form == "SF330"
    dit = notice.find_department(info, "DIT", "Department of Information Technology")
    assert dit is not None
    assert {c["marker"] for c in dit.categories} >= set("abcdef")  # lettered sub-items


def test_validate_fy_match_and_mismatch(info):
    store = {"opportunity": {"department": "DIT", "fiscal_year": 2026,
                             "selected_categories": ["1", "2", "6"]}}
    rep = notice.validate(info, store)
    assert _status(rep, "Fiscal year") == PASS
    assert _status(rep, "Selected categories") == PASS

    rep2 = notice.validate(info, store, target_fy=2027)
    assert _status(rep2, "Fiscal year") == FAIL


def test_validate_flags_out_of_range_category(info):
    store = {"opportunity": {"department": "DIT", "fiscal_year": 2026,
                             "selected_categories": ["1", "99"]}}  # 99 -> beyond a-z
    rep = notice.validate(info, store)
    assert _status(rep, "Selected categories") == FAIL


def test_validate_flags_missing_sf330(info):
    store = {"opportunity": {"department": "DDC", "fiscal_year": 2026,
                             "required_form": "general", "selected_categories": []}}
    rep = notice.validate(info, store)
    assert _status(rep, "Required form") == FAIL   # notice wants SF330


def test_find_notice_pdf(tmp_path):
    assert notice.find_notice_pdf(tmp_path) is None
    (tmp_path / "Professional-Services-Annual-Ad-Fiscal-Year-2027.pdf").write_bytes(b"%PDF-")
    found = notice.find_notice_pdf(tmp_path)
    assert found and found.name.startswith("Professional-Services")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
