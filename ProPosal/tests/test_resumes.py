"""Tests for personnel <-> resumes-folder cross-verification."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import resumes  # noqa: E402
from proposal.flags import Report  # noqa: E402


def _make_folder(tmp_path, names):
    for n in names:
        (tmp_path / n).write_bytes(b"x")
    return tmp_path


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


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
