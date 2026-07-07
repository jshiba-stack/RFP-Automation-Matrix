"""Category ids must be unique even when the DIT # is blank/'?'.

Regression for the `cat-item` collision: two unlettered rows used to get the
same id (slug of '?') and later clobbered each other on edit/accept.
"""

import sys
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal.tools.extract_store import extract  # noqa: E402


def test_unlettered_categories_get_distinct_ids(tmp_path):
    doc = Document()
    t = doc.add_table(rows=1, cols=3)
    for i, h in enumerate(("DIT #", "Professional Service Category", "Description")):
        t.rows[0].cells[i].text = h
    for dit, name in [("a", "Oracle Databases"),
                      ("?", "Internet and E-Commerce"),
                      ("?", "IT Portfolio and Project Management")]:
        r = t.add_row()
        r.cells[0].text, r.cells[1].text = dit, name
    p = tmp_path / "mini.docx"
    doc.save(str(p))

    cats = extract(str(p))["categories"]
    ids = [c["id"] for c in cats]
    assert len(ids) == len(set(ids)), f"category ids must be unique, got {ids}"
    # ids are keyed off the name, not the '?'
    assert any("internet" in i for i in ids) and any("portfolio" in i for i in ids)
