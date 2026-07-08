"""Fill PDF AcroForm forms (DPW-120 now; any fillable PDF) from the data store.

Two modes, mirroring the docx pipeline:
  * generate (2b-style): fill a blank template's fields from the data store.
  * carry-forward (2a-style): seed values from a previously-filled copy of the
    form -- every field whose NAME matches is carried over -- then overlay the
    store, and flag fields that don't line up (blank in the new template, or
    present in the old fill but absent from the new template).

Everything is flag-only; the engine never invents data, it leaves unmapped
fields blank and reports them.
"""

from __future__ import annotations

import datetime as _dt
from io import BytesIO

from pypdf import PdfReader, PdfWriter

from .flags import KIND_ADD, KIND_MISSING, KIND_REVIEW, Report


def read_fields(pdf_path) -> dict[str, str]:
    """Return ``{field_name: current_value}`` for a fillable PDF (empty if flat)."""
    reader = PdfReader(str(pdf_path))
    fields = reader.get_fields() or {}
    out = {}
    for name, f in fields.items():
        val = f.get("/V")
        out[name] = "" if val is None else str(val)
    return out


def field_names(pdf_path) -> list[str]:
    return list(read_fields(pdf_path).keys())


def _resolve(store: dict, spec: str, today: _dt.date) -> str:
    if spec == "@today":
        return f"{today:%B} {today.day}, {today.year}"
    cur = store
    for part in spec.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return ""
    if isinstance(cur, list):
        return "\n".join(str(x) for x in cur)
    if isinstance(cur, dict):
        return ""
    return str(cur)


def _write_filled(template_path, values: dict) -> bytes:
    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, values, auto_regenerate=False)
        except Exception:  # noqa: BLE001 - some pages have no fields
            pass
    try:
        writer.set_need_appearances_writer(True)  # so viewers render the values
    except Exception:  # noqa: BLE001
        pass
    bio = BytesIO()
    writer.write(bio)
    return bio.getvalue()


def fill(template_path, field_map: dict, store: dict | None = None, *,
         prev_filled=None, today: _dt.date | None = None):
    """Return ``(pdf_bytes | None, Report)``. ``None`` if the template is flat."""
    store = store or {}
    today = today or _dt.date.today()
    report = Report(base=str(template_path))

    names = field_names(template_path)
    if not names:
        report.flag("template",
                    "This template has no fillable fields (flat PDF). Provide a fillable template.",
                    KIND_MISSING)
        return None, report

    values: dict[str, str] = {}

    # 2a-style: carry forward from a previously-filled copy (match by field name)
    if prev_filled:
        prev = read_fields(prev_filled)
        name_set = set(names)
        carried = 0
        for k, v in prev.items():
            if k in name_set and str(v).strip():
                values[k] = v
                carried += 1
        if carried:
            report.applied("carry-forward", f"carried {carried} field(s) from the previous form")
        for k, v in prev.items():
            if k not in name_set and str(v).strip():
                report.flag("carry-forward",
                            f"Previous form has '{k}' but the new template doesn't -- verify.",
                            KIND_REVIEW, new=str(v)[:60])

    # 2b-style: overlay store-mapped fields
    for acro_field, spec in field_map.items():
        if acro_field not in names:
            continue
        val = _resolve(store, spec, today)
        if val:
            values[acro_field] = val
            report.applied(acro_field, "filled from data store", new=val.replace("\n", " ")[:60])

    pdf_bytes = _write_filled(template_path, values)

    # flag fields left blank after both passes
    blank = [n for n in names if not str(values.get(n, "")).strip()]
    if blank:
        sample = ", ".join(blank[:8]) + ("  ..." if len(blank) > 8 else "")
        report.flag("blank fields",
                    f"{len(blank)} field(s) left blank -- fill manually or extend the map: {sample}",
                    KIND_ADD)

    return pdf_bytes, report
