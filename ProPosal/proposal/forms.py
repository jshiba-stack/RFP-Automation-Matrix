"""Registry of supported fillable forms.

Each form has a default (blank) template and a field map: AcroForm field name ->
a store "spec" the engine resolves. Specs are either ``@today`` or a dotted path
into the data store (``firm.legal_name``); a list value is newline-joined.

The map here is intentionally tiny (framework demo) -- the full DPW-120 has 276
fields. Extend ``field_map`` as the data store gains the matching data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FormSpec:
    key: str
    name: str
    default_template: str           # path relative to the ProPosal root
    field_map: dict                 # acroform field name -> store spec
    notes: str = ""


# --- DPW-120 (fillable AcroForm) -- tiny demo map ---------------------------
DPW120_MAP = {
    "FIRM NAME": "firm.legal_name",
    "DATE": "@today",
    "BUSINESS ADDRESS TELEPHONE  FAX NO OF HAWAII OFFICE": "firm.address_lines",
    "PRINCIPALS OF FIRM NAMES": "firm.signatory.name",
}

FORMS = {
    "DPW-120": FormSpec(
        key="DPW-120",
        name="DPW-120 Statement of Qualifications",
        default_template="assets/defaults/DPW-120-fillable.pdf",
        field_map=DPW120_MAP,
        notes="Fillable AcroForm (276 fields). Demo map fills a few; extend as needed.",
    ),
    "SF330": FormSpec(
        key="SF330",
        name="Modified Standard Form 330",
        default_template="assets/defaults/Modified-SF330_Qualification_Form.pdf",
        field_map={},
        notes="The bundled PDF is flat (no form fields). Provide a fillable SF330 template to use this.",
    ),
}
