"""Tests for the resume-PDF typography lint (pdfutil.resume_pdf_issues).

Real-world reference: resumes re-saved with a desktop PDF editor (PDFescape)
came out with text drawn at unequal x/y scale (words look vertically
stretched) and Arial swapped in un-embedded. The lint must catch those
signatures; clean Word exports must pass silently.
"""

import os
import sys
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import pdfutil, resumes  # noqa: E402

HELVETICA = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
ARIAL_NOEMBED = "<< /Type /Font /Subtype /TrueType /BaseFont /ArialMT >>"


def _raw_pdf(path: Path, content: bytes = b"", fonts: dict | None = None,
             mediabox: str = "0 0 612 792") -> Path:
    """A minimal hand-built one-page PDF with full control over the content
    stream and font resources (pypdf's writer can't author text runs)."""
    fonts = fonts or {}
    font_entries = " ".join(f"{n} {5 + i} 0 R" for i, n in enumerate(fonts))
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (f"<< /Type /Page /Parent 2 0 R /MediaBox [{mediabox}] "
            f"/Contents 4 0 R /Resources << /Font << {font_entries} >> >> "
            ">>").encode(),
        4: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
    }
    for i, fdict in enumerate(fonts.values()):
        objs[5 + i] = fdict.encode()
    n = max(objs) + 1
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objs[num] + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % n
    for num in range(1, n):
        out += b"%010d 00000 n \n" % offsets[num]
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (n, xref_pos))
    path.write_bytes(bytes(out))
    return path


def _text_content(sy: float, runs: int = 6) -> bytes:
    lines = [
        f"BT /F1 10 Tf 1 0 0 {sy} 72 {700 - 14 * i} Tm (Hello World run) Tj ET"
        for i in range(runs)
    ]
    return "\n".join(lines).encode()


def _word_pdf(path: Path, creator="Microsoft Word", pages=1, mtime=None) -> Path:
    w = pypdf.PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=612, height=792)
    w.add_metadata({"/Creator": creator, "/Producer": "Microsoft Word for Microsoft 365"})
    with open(path, "wb") as fh:
        w.write(fh)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_stretched_text_is_flagged(tmp_path):
    p = _raw_pdf(tmp_path / "r.pdf", _text_content(sy=1.33), {"/F1": HELVETICA})
    issues = pdfutil.resume_pdf_issues(p)
    assert any("stretched" in i for i in issues), issues
    assert any("33%" in i and "taller" in i for i in issues), issues


def test_uniform_text_and_standard_font_pass(tmp_path):
    # 1:1 scale + un-embedded base-14 Helvetica: both are fine.
    p = _raw_pdf(tmp_path / "r.pdf", _text_content(sy=1.0), {"/F1": HELVETICA})
    assert pdfutil.resume_pdf_issues(p) == []


def test_a_few_stretched_runs_are_tolerated(tmp_path):
    # under 5 odd runs (a scaled logo caption etc.) shouldn't cry wolf
    p = _raw_pdf(tmp_path / "r.pdf", _text_content(sy=1.33, runs=3),
                 {"/F1": HELVETICA})
    assert pdfutil.resume_pdf_issues(p) == []


def test_nonembedded_nonstandard_font_is_flagged(tmp_path):
    p = _raw_pdf(tmp_path / "r.pdf", b"", {"/F1": ARIAL_NOEMBED})
    issues = pdfutil.resume_pdf_issues(p)
    assert any("ArialMT" in i and "embedded" in i for i in issues), issues


def test_off_letter_page_is_flagged(tmp_path):
    p = _raw_pdf(tmp_path / "r.pdf", mediabox="0 0 595 842")  # A4
    issues = pdfutil.resume_pdf_issues(p)
    assert any("595" in i and "Letter" in i for i in issues), issues


def test_editor_resave_is_detected_and_flagged(tmp_path):
    p = _word_pdf(tmp_path / "r.pdf", creator="PDFescape Desktop")
    assert pdfutil.pdf_editor_rewrite(p) == "PDFescape Desktop"
    issues = pdfutil.resume_pdf_issues(p)
    assert any("PDFescape" in i and "re-saved" in i for i in issues), issues


def test_clean_word_export_passes(tmp_path):
    p = _word_pdf(tmp_path / "r.pdf")
    assert pdfutil.pdf_editor_rewrite(p) is None
    assert pdfutil.resume_pdf_issues(p) == []


def _docx_1p(path: Path, mtime=None) -> Path:
    import zipfile
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("docProps/app.xml", "<Properties><Pages>1</Pages></Properties>")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_pick_swaps_reedited_pdf_for_same_generation_clean_pdf(tmp_path):
    # clean export ~6 days older than the re-edited copy: same generation
    _word_pdf(tmp_path / "avery clean.pdf", mtime=2_000_000_000)
    _word_pdf(tmp_path / "avery edited.pdf", creator="PDFescape Desktop",
              mtime=2_000_500_000)
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    (name, hit), = res["matched"]
    assert hit.name == "avery clean.pdf"
    assert "re-saved with PDFescape Desktop" in res["notes"][name]


def test_pick_swaps_reedited_pdf_for_same_generation_docx(tmp_path):
    # only sibling is a .docx ~12 days older: Word conversion beats mangled PDF
    _word_pdf(tmp_path / "avery.pdf", creator="PDFescape Desktop",
              mtime=2_000_000_000)
    _docx_1p(tmp_path / "avery.docx", mtime=1_999_000_000)
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    (name, hit), = res["matched"]
    assert hit.name == "avery.docx"
    assert "re-saved" in res["notes"][name]


def test_stale_clean_copy_never_beats_newer_content(tmp_path):
    # the only clean copy is years old -- freshness wins, lint flags the pick
    _word_pdf(tmp_path / "avery 2023.pdf", mtime=1_000_000_000)
    _word_pdf(tmp_path / "avery 2026.pdf", creator="PDFescape Desktop",
              mtime=2_000_000_000)
    res = resumes.cross_check([{"name": "Jordan Avery"}], tmp_path)
    (name, hit), = res["matched"]
    assert hit.name == "avery 2026.pdf"
    assert "newest 1-page .pdf" in res["notes"][name]




# --- letterhead stamping ------------------------------------------------------

def _lh_content(lines, x=400, y0=758, pitch=12, size=10, extra=b""):
    ops = []
    for i, line in enumerate(lines):
        ops.append(f"BT /F1 {size} Tf 1 0 0 1 {x} {y0 - i * pitch} Tm ({line}) Tj ET")
    return ("\n".join(ops)).encode() + b"\n" + extra


FICTION_LH = ["Acme Fictional, LLC", "123 Example Rd, Ste 9",
              "Springfield, HI 96800", "www.example.test"]


def test_letterhead_spec_measures_body(tmp_path):
    body = _raw_pdf(tmp_path / "body.pdf", _lh_content(FICTION_LH),
                    {"/F1": HELVETICA})
    spec = pdfutil.letterhead_spec(body)
    assert spec is not None
    assert spec["lines"] == FICTION_LH
    assert abs(spec["pitch"] - 12) < 0.1
    assert spec["size"] == 10


def test_stamp_letterhead_replaces_block(tmp_path):
    from pypdf import PdfReader
    resume = _raw_pdf(tmp_path / "res.pdf", _lh_content(
        ["Acme Fictional", "123 Example Rd", "Springfield, HI 96800"],
        x=420, y0=760, size=9,
        extra=b"BT /F1 12 Tf 1 0 0 1 72 600 Tm (JORDAN AVERY resume body) Tj ET"),
        {"/F1": HELVETICA})
    stamp = _raw_pdf(tmp_path / "stamp.pdf", _lh_content(FICTION_LH),
                     {"/F1": HELVETICA})
    out, why = pdfutil.stamp_letterhead(resume, stamp, tmp_path / "out.pdf")
    assert out is not None, why
    text = PdfReader(str(out)).pages[0].extract_text()
    assert "www.example.test" in text            # stamp content present
    assert "JORDAN AVERY resume body" in text    # body untouched


def test_stamp_letterhead_refuses_unknown_header_text(tmp_path):
    resume = _raw_pdf(tmp_path / "res.pdf", _lh_content(
        ["Top Secret Addendum"]), {"/F1": HELVETICA})
    stamp = _raw_pdf(tmp_path / "stamp.pdf", _lh_content(FICTION_LH),
                     {"/F1": HELVETICA})
    out, why = pdfutil.stamp_letterhead(resume, stamp, tmp_path / "out.pdf")
    assert out is None
    assert "Top Secret" in why


def _pdf_with_image(path: Path, cm=(111, 0, 0, 54, 72, 702)) -> Path:
    """One-page PDF drawing a 1x1 image scaled to a logo-sized rect."""
    content = (f"q {cm[0]} {cm[1]} {cm[2]} {cm[3]} {cm[4]} {cm[5]} cm "
               "/Im1 Do Q").encode()
    img = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
           b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 3 >>\n"
           b"stream\n\xff\x00\x00\nendstream")
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /XObject << /Im1 5 0 R >> >> >>"),
        4: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        5: img,
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objs[num] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += b"%010d 00000 n \n" % offsets[num]
    out += (b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % xref)
    path.write_bytes(bytes(out))
    return path


def test_logo_top_from_image_placement(tmp_path):
    # rect 72..183 x, top edge at 792-(702+54) = 36pt (top-down)
    p = _pdf_with_image(tmp_path / "r.pdf", cm=(111, 0, 0, 54, 72, 702))
    assert abs(pdfutil.logo_top(p) - 36.0) < 0.1
    # no image -> None
    q = _raw_pdf(tmp_path / "plain.pdf")
    assert pdfutil.logo_top(q) is None


def test_stamp_letterhead_dy_shifts_block_down(tmp_path):
    resume = _raw_pdf(tmp_path / "res.pdf",
                      _lh_content(["Acme Fictional, LLC"]), {"/F1": HELVETICA})
    stamp = _raw_pdf(tmp_path / "stamp.pdf", _lh_content(FICTION_LH),
                     {"/F1": HELVETICA})
    out, why = pdfutil.stamp_letterhead(resume, stamp, tmp_path / "out.pdf",
                                        dy=7.6)
    assert out is not None, why
    lines = {t: y for y, _x, _s, t in
             pdfutil._zone_lines(pdfutil._zone_runs(out))}
    # stamp line moved down by dy vs its position in the stamp itself
    orig = {t: y for y, _x, _s, t in
            pdfutil._zone_lines(pdfutil._zone_runs(stamp))}
    assert abs(lines["www.example.test"] - (orig["www.example.test"] + 7.6)) < 0.2


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
