"""PDF measurement helpers for the compliance checklist.

We never render the deliverable PDF ourselves -- only Word produces a faithful
submittal. These helpers MEASURE a PDF the user exported (size, page count), and
optionally drive Word (via docx2pdf, Windows only) to produce a throwaway PDF
purely for measurement when ``auto_export_pdf`` is enabled.
"""

from __future__ import annotations

import os
from pathlib import Path


def pdf_size_mb(path) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def pdf_page_count(path) -> int | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def find_companion_pdf(docx_path) -> Path | None:
    """A PDF the user exported next to the .docx (same stem) if one exists."""
    p = Path(docx_path)
    cand = p.with_suffix(".pdf")
    return cand if cand.exists() else None


def export_pdf(docx_path, out_pdf=None) -> Path | None:
    """Export docx -> pdf via Word (docx2pdf). Returns the path or None.

    Windows + Word only; used solely to MEASURE size/pages. The user's own export
    remains the authoritative deliverable.
    """
    try:
        from docx2pdf import convert
    except Exception:
        return None
    out = Path(out_pdf) if out_pdf else Path(docx_path).with_suffix(".measure.pdf")
    try:
        convert(str(docx_path), str(out))
    except Exception:
        return None
    return out if out.exists() else None
