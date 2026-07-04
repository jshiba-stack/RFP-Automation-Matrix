"""Table proofread pass: normalize font size + interior borders (auto-fix).

Content imported/edited from a previous draft drifts: a few rows in a table end
up a point smaller than their neighbours, or a past-performance block loses the
interior border a sibling block still has. Word never complains, but it reads as
sloppy in a submittal.

This pass runs after the build/generate engines produce the document and before
it is saved. For each body table it enforces *internal* consistency -- every data
row at the table's own dominant font size, and every table in a family at the
family's majority interior-border pattern -- then records what it did:

* each concrete change -> an APPLIED record (the "changelog"), and
* each affected table -> a single REVIEW flag, so the human double-checks the
  auto-fix rather than trusting it blindly.

Nothing is decided from a hardcoded house style; the target is always whatever
the surrounding content already agrees on, so the pass is conservative and safe
to run every build.
"""

from __future__ import annotations

import copy
from collections import Counter

from docx.oxml.ns import qn
from lxml import etree
from docx.shared import Emu

from . import docx_map
from .flags import KIND_REVIEW

# child order within <w:tblBorders> and <w:tblPr> (subset), so inserted
# elements land in a schema-valid position.
_BORDERS_ORDER = [qn(f"w:{t}") for t in
                  ("top", "left", "bottom", "right", "insideH", "insideV")]
_TBLPR_ORDER = [qn(f"w:{t}") for t in (
    "tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
    "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd",
    "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook")]


# --- labels -----------------------------------------------------------------

def _table_label(tbl, ordinal: int) -> str:
    """Human-readable place for a table, keyed off its header signature."""
    sig = docx_map._table_signature(tbl)
    letter = chr(ord("A") + ordinal) if ordinal < 26 else f"#{ordinal + 1}"
    if sig == docx_map.SIG_QUALIFICATIONS:
        return "Section II · Qualifications"
    if sig == docx_map.SIG_CAPACITY:
        return "Section IV · Capacity"
    if len(sig) == 2 and sig[0] == docx_map.SIG_PASTPERF_FIRST_CELL:
        client = tbl.rows[0].cells[1].text.strip().splitlines()[0] if tbl.rows else ""
        return f"Section III · Past performance ({client})" if client \
            else f"Section III · Past performance (Table {letter})"
    return f"Table {letter}"


# --- font size --------------------------------------------------------------

def _normal_size(doc):
    try:
        return doc.styles["Normal"].font.size
    except (KeyError, AttributeError):
        return None


def _effective_size(run, para, normal_size):
    """The size a run actually renders at: explicit run size, else the nearest
    paragraph-style size up the base-style chain, else the Normal default."""
    if run.font.size is not None:
        return run.font.size
    style = para.style
    seen = 0
    while style is not None and seen < 10:
        if getattr(style, "font", None) is not None and style.font.size is not None:
            return style.font.size
        style = getattr(style, "base_style", None)
        seen += 1
    return normal_size


def _fmt_pt(length) -> str:
    return f"{length.pt:g}pt" if length is not None else "default"


def _size_tally(data_rows, normal) -> Counter:
    """Count effective font sizes (EMU) across non-empty data-row runs."""
    tally = Counter()
    for row in data_rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    if not run.text.strip():
                        continue
                    eff = _effective_size(run, para, normal)
                    if eff is not None:
                        tally[int(eff)] += 1
    return tally


def _normalize_font(doc, report, log) -> int:
    """Bring every table's data rows to that table's dominant font size."""
    normal = _normal_size(doc)
    changed_tables = 0
    for ordinal, tbl in enumerate(doc.tables):
        data_rows = tbl.rows[1:]
        if not data_rows:
            continue
        tally = _size_tally(data_rows, normal)
        if len(tally) < 2:
            continue  # already uniform (or unknowable) -> nothing to do
        target_emu, _ = tally.most_common(1)[0]
        target = Emu(target_emu)

        rows_changed = 0
        olds: set[str] = set()
        for row_i, row in enumerate(data_rows, start=1):
            row_touched = False
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if not run.text.strip():
                            continue
                        eff = _effective_size(run, para, normal)
                        if eff is None or int(eff) == target_emu:
                            continue
                        olds.add(_fmt_pt(eff))
                        run.font.size = target
                        row_touched = True
            if row_touched:
                rows_changed += 1
                report.applied(
                    f"{_table_label(tbl, ordinal)} r{row_i}",
                    f"font size {' / '.join(sorted(olds))} -> {_fmt_pt(target)}")
                olds.clear()
        if rows_changed:
            changed_tables += 1
            report.flag(
                _table_label(tbl, ordinal),
                f"normalized {rows_changed} row(s) to {_fmt_pt(target)} font — verify",
                KIND_REVIEW)
            log(f"[proofread] {_table_label(tbl, ordinal)}: "
                f"{rows_changed} row(s) -> {_fmt_pt(target)}")
    return changed_tables


# --- interior borders -------------------------------------------------------

def _insert_in_order(parent, child, order):
    """Append ``child`` to ``parent`` at its schema-ordered position."""
    if child.tag not in order:
        parent.append(child)
        return
    rank = order.index(child.tag)
    for existing in parent:
        if existing.tag in order and order.index(existing.tag) > rank:
            existing.addprevious(child)
            return
    parent.append(child)


def _inside_h(tbl):
    borders = tbl._tbl.tblPr.find(qn("w:tblBorders"))
    return None if borders is None else borders.find(qn("w:insideH"))


def _is_real_border(el) -> bool:
    if el is None:
        return False
    return el.get(qn("w:val")) not in (None, "nil", "none")


def _set_inside_h(tbl, model_el) -> None:
    tblPr = tbl._tbl.tblPr
    borders = tblPr.find(qn("w:tblBorders"))
    if borders is None:
        borders = tblPr.makeelement(qn("w:tblBorders"), {})
        _insert_in_order(tblPr, borders, _TBLPR_ORDER)
    existing = borders.find(qn("w:insideH"))
    if existing is not None:
        borders.remove(existing)
    _insert_in_order(borders, copy.deepcopy(model_el), _BORDERS_ORDER)


def _family_key(tbl):
    """Group tables that should share a border pattern. Past-performance blocks
    (2-col, first cell 'Client') form one family regardless of client name; every
    other table is grouped by its exact header signature."""
    sig = docx_map._table_signature(tbl)
    if len(sig) == 2 and sig[0] == docx_map.SIG_PASTPERF_FIRST_CELL:
        return ("pastperf",)
    return sig


def _normalize_borders(doc, report, log) -> int:
    """Within each table family, give a deficient table the majority interior
    horizontal border its siblings already carry."""
    families: dict[tuple, list[tuple[int, object]]] = {}
    for ordinal, tbl in enumerate(doc.tables):
        families.setdefault(_family_key(tbl), []).append((ordinal, tbl))

    fixed = 0
    for members in families.values():
        if len(members) < 2:
            continue  # no sibling to agree with
        real = [(o, t, _inside_h(t)) for o, t in members if _is_real_border(_inside_h(t))]
        if not real or len(real) == len(members):
            continue  # nobody has one, or everybody does -> nothing to reconcile
        # majority border XML among the tables that have a real one
        by_xml = Counter(etree.tostring(el) for _, _, el in real)
        model_xml, _ = by_xml.most_common(1)[0]
        model_el = next(el for _, _, el in real if etree.tostring(el) == model_xml)
        for ordinal, tbl in members:
            if _is_real_border(_inside_h(tbl)):
                continue
            _set_inside_h(tbl, model_el)
            fixed += 1
            label = _table_label(tbl, ordinal)
            report.applied(label, "added interior row border to match sibling tables")
            report.flag(label, "added missing interior row border — verify", KIND_REVIEW)
            log(f"[proofread] {label}: added interior border")
    return fixed


# --- read-only detectors (for the format checker) ---------------------------

def font_outliers(doc) -> list[str]:
    """Labels of tables whose data rows do not all share one font size."""
    normal = _normal_size(doc)
    out = []
    for ordinal, tbl in enumerate(doc.tables):
        data_rows = tbl.rows[1:]
        if data_rows and len(_size_tally(data_rows, normal)) >= 2:
            out.append(_table_label(tbl, ordinal))
    return out


def border_outliers(doc) -> list[str]:
    """Labels of tables missing an interior border a sibling table carries."""
    families: dict[tuple, list[tuple[int, object]]] = {}
    for ordinal, tbl in enumerate(doc.tables):
        families.setdefault(_family_key(tbl), []).append((ordinal, tbl))
    out = []
    for members in families.values():
        if len(members) < 2:
            continue
        haves = [_is_real_border(_inside_h(t)) for _, t in members]
        if any(haves) and not all(haves):
            out.extend(_table_label(t, o) for (o, t), has in zip(members, haves) if not has)
    return out


# --- entry point ------------------------------------------------------------

def proofread_document(doc, report, log=print) -> dict:
    """Normalize table font sizes and interior borders in place.

    Records every change in ``report`` (APPLIED + a REVIEW flag per table).
    Returns a small summary dict for callers/tests.
    """
    fonts = _normalize_font(doc, report, log)
    borders = _normalize_borders(doc, report, log)
    if fonts or borders:
        log(f"[proofread] normalized {fonts} table(s) for font size, "
            f"{borders} for borders.")
    return {"font_tables": fonts, "border_tables": borders}
