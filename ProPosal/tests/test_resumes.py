"""Tests for personnel <-> resumes-folder cross-verification."""

import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import resumes  # noqa: E402
from proposal.flags import Report  # noqa: E402


def _make_folder(tmp_path, names):
    for n in names:
        (tmp_path / n).write_bytes(b"x")
    return tmp_path


def _docx(path: Path, pages: int, mtime: float | None = None) -> Path:
    """A minimal .docx-shaped zip carrying a Word page count in app.xml."""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("docProps/app.xml",
                   f"<Properties><Pages>{pages}</Pages></Properties>")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_cross_check_matches_missing_and_orphans(tmp_path):
    _make_folder(tmp_path, ["Avery.docx", "rivera_sam.pdf", "stranger.docx", "notes.txt"])
    personnel = [
        {"name": "Jordan Avery"},
        {"name": "Sam Rivera"},
        {"name": "Nobody Here"},
    ]
    res = resumes.cross_check(personnel, tmp_path)
    matched_names = {n for n, _ in res["matched"]}
    assert matched_names == {"Jordan Avery", "Sam Rivera"}
    assert res["missing"] == ["Nobody Here"]
    orphan_names = {f.name for f in res["orphans"]}
    assert orphan_names == {"stranger.docx"}            # notes.txt isn't a resume ext


def test_add_resume_flags_populates_report(tmp_path):
    _make_folder(tmp_path, ["avery.docx", "newhire.docx"])
    report = Report()
    store = {"personnel": [{"name": "Jordan Avery"}, {"name": "Gone Away"}]}
    resumes.add_resume_flags(report, store, tmp_path)
    kinds = {(f.kind, f.summary[:18]) for f in report.flags}
    assert any(k == "REVIEW" and "No resume" in s for k, s in
               {(f.kind, f.summary) for f in report.flags})
    assert any("newhire.docx" in f.new for f in report.flags)


def test_no_folder_is_noop(tmp_path):
    report = Report()
    res = resumes.add_resume_flags(report, {"personnel": [{"name": "X"}]}, tmp_path / "missing")
    assert res["matched"] == [] and not report.flags


def test_multi_file_prefers_newest_one_pager(tmp_path):
    _docx(tmp_path / "avery_full.docx", pages=3, mtime=2_000_000_000)   # newest but long
    _docx(tmp_path / "avery_1pg_old.docx", pages=1, mtime=1_000_000_000)
    _docx(tmp_path / "avery_1pg_new.docx", pages=1, mtime=1_500_000_000)
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    (name, hit), = res["matched"]
    assert hit.name == "avery_1pg_new.docx"          # newest ONE-PAGE, not newest overall
    assert res["notes"][name] == "newest 1-page .docx of 3 matching files"
    assert {f.name for f, _owner in res["alternates"]} == {"avery_full.docx", "avery_1pg_old.docx"}
    assert res["orphans"] == []                      # alternates aren't "new hire?" noise
    report = Report()
    resumes.add_resume_flags(report, {"personnel": [{"name": "Jordan Avery"}]}, tmp_path)
    assert not report.flags                          # confident pick -> no flag


def _pdf(path, pages=1, mtime=None):
    import pypdf
    w = pypdf.PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=612, height=792)
    with open(path, "wb") as fh:
        w.write(fh)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_one_page_pdf_beats_newer_one_page_docx(tmp_path):
    # the submittal is assembled from PDF pages, so the PDF export wins
    _pdf(tmp_path / "avery_1pg.pdf", mtime=1_000_000_000)
    _docx(tmp_path / "avery_1pg.docx", pages=1, mtime=2_000_000_000)
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    (_, hit), = res["matched"]
    assert hit.name == "avery_1pg.pdf"


def test_merge_pdfs_concatenates_in_order(tmp_path):
    from pypdf import PdfReader

    from proposal import pdfutil
    a = _pdf(tmp_path / "a.pdf", pages=2)
    b = _pdf(tmp_path / "b.pdf", pages=1)
    c = _pdf(tmp_path / "c.pdf", pages=3)
    merged = pdfutil.merge_pdfs([a, b, c])
    out = tmp_path / "merged.pdf"
    out.write_bytes(merged)
    assert len(PdfReader(str(out)).pages) == 6


def test_multi_file_no_one_pager_falls_back_to_newest_and_flags(tmp_path):
    _docx(tmp_path / "avery_v1.docx", pages=2, mtime=1_000_000_000)
    _docx(tmp_path / "avery_v2.docx", pages=3, mtime=2_000_000_000)
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    (_, hit), = res["matched"]
    assert hit.name == "avery_v2.docx"
    report = Report()
    resumes.add_resume_flags(report, {"personnel": [{"name": "Jordan Avery"}]}, tmp_path)
    assert any("none is one page" in f.summary and f.kind == "REVIEW" for f in report.flags)


def test_per_person_subfolders_match_by_folder_name(tmp_path):
    # folder name identifies the person; file names don't mention them at all
    (tmp_path / "Jordan Avery").mkdir()
    _docx(tmp_path / "Jordan Avery" / "Resume 2024.docx", pages=1, mtime=1_500_000_000)
    _docx(tmp_path / "Jordan Avery" / "Resume 2019.docx", pages=1, mtime=1_000_000_000)
    (tmp_path / "Sam Rivera").mkdir()
    _docx(tmp_path / "Sam Rivera" / "CV long.docx", pages=4, mtime=1_000_000_000)
    (tmp_path / "Unrelated Docs").mkdir()
    (tmp_path / "Unrelated Docs" / "brochure.pdf").write_bytes(b"x")
    (tmp_path / "Jordan Avery" / "~$Resume 2024.docx").write_bytes(b"lock")  # Word temp

    personnel = [{"name": "Jordan Avery"}, {"name": "Sam Rivera"}]
    res = resumes.cross_check(personnel, tmp_path)
    picked = {n: p for n, p in res["matched"]}
    assert picked["Jordan Avery"].name == "Resume 2024.docx"   # newest 1-pager in folder
    assert picked["Sam Rivera"].name == "CV long.docx"
    assert res["missing"] == []
    assert {f.name for f, _o in res["alternates"]} == {"Resume 2019.docx"}
    assert {f.name for f in res["orphans"]} == {"brochure.pdf"}


def test_shared_surname_full_name_wins(tmp_path):
    # Two people share a surname, each with their own folder. The last-name
    # fallback must not steal a stronger (full-name) candidate's files.
    for person, mt in (("Kai Watson", 2_000_000_000), ("Bo Watson", 1_000_000_000)):
        (tmp_path / person).mkdir()
        _docx(tmp_path / person / f"{person} - 1P.docx", pages=1, mtime=mt)
        _docx(tmp_path / person / f"{person} - long.docx", pages=3, mtime=mt)
    personnel = [{"name": "Kai Watson"}, {"name": "Bo Watson"}]
    res = resumes.cross_check(personnel, tmp_path)
    picked = {n: p for n, p in res["matched"]}
    assert picked["Kai Watson"].parent.name == "Kai Watson"
    assert picked["Bo Watson"].parent.name == "Bo Watson"   # not Kai's newer file
    assert picked["Bo Watson"].name == "Bo Watson - 1P.docx"


def test_page_count_unknown_is_tolerated(tmp_path):
    (tmp_path / "avery.doc").write_bytes(b"legacy")   # .doc: page count unknowable
    assert resumes.page_count(tmp_path / "avery.doc") is None
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    assert res["matched"][0][1].name == "avery.doc"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
