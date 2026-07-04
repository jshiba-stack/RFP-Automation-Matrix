"""Tests for the store-extractor and generate-from-data-store mode."""

import sys
from pathlib import Path

import pytest
from docx import Document

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import docx_map, generator  # noqa: E402
from proposal.tools import extract_store  # noqa: E402

BASE = next(iter(sorted((ROOT / "assets/refs").glob("*FINAL*.docx"))), ROOT / "assets/refs/__none__.docx")
pytestmark = pytest.mark.skipif(not BASE.exists(), reason="reference FINAL not available")


@pytest.fixture(scope="module")
def store():
    return extract_store.extract(str(BASE))


def test_extract_pulls_all_sections(store):
    assert store["opportunity"]["fiscal_year"] == 2026
    assert len(store["categories"]) >= 10
    assert len(store["personnel"]) == 10
    assert len(store["projects"]) == 7
    assert len(store["past_performance"]) >= 6
    # ongoing detection: '2025+' -> 'ongoing'; completed -> int year
    ends = {p["end"] for p in store["projects"]}
    assert "ongoing" in ends and 2024 in ends


def test_extract_past_performance_full_blocks(store):
    ids = [r["id"] for r in store["past_performance"]]
    assert len(ids) == len(set(ids))                     # unique even for same client
    rec = store["past_performance"][0]
    for field in ("client", "project", "scope", "issue_resolution"):
        assert rec.get(field), f"missing {field}"
    assert "\n" not in rec["client"]                     # client reads on one line


def test_generate_rebuilds_capacity_from_store(store):
    doc, report = generator.generate(BASE, store, target_fy=2027, cover_date="2026-03-02")
    cap = docx_map.find_capacity_table(doc)
    body = cap.rows[1:]
    assert len(body) == len(store["projects"])
    # ongoing rows render '<cover-year>+'; completed render the literal year
    rendered = {r.cells[3].text.strip() for r in body}
    assert "2026+" in rendered
    assert "2024" in rendered and "2025+" not in rendered
    # fiscal year + dates applied
    from proposal.docx_edit import iter_all_paragraphs, para_text
    joined = "\n".join(para_text(p) for p in iter_all_paragraphs(doc))
    assert "Fiscal Year 2027" in joined and "March 2, 2026" in joined


def test_generate_rebuilds_qualifications(store):
    doc, _ = generator.generate(BASE, store, target_fy=2027)
    q = docx_map.find_table_by_signature(doc, docx_map.SIG_QUALIFICATIONS)[0]
    names = [r.cells[0].text.strip() for r in q.rows[1:]]
    assert store["personnel"][0]["name"] in names   # first person from the store
    assert len(names) == len(store["personnel"])


def test_generate_without_resumes_folder_flags_once(store):
    _, report = generator.generate(BASE, store, target_fy=2027)
    folder_flags = [f for f in report.flags if "resumes folder" in f.summary.lower()]
    assert len(folder_flags) == 1


def test_generate_with_resumes_folder_cross_checks(store, tmp_path):
    # one matching resume on file; the rest should be flagged missing
    last_name = store["personnel"][0]["name"].split()[-1]
    (tmp_path / f"{last_name}.docx").write_bytes(b"x")
    _, report = generator.generate(BASE, store, target_fy=2027, resumes_dir=str(tmp_path))
    missing = [f for f in report.flags if f.kind == "REVIEW" and "No resume" in f.summary]
    assert len(missing) == len(store["personnel"]) - 1   # all but the one with a resume


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
