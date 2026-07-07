# Default / mandatory reference documents

This folder holds the **standing reference documents** ProPosal compares against or
fills — the City & County annual *Notice to Providers of Professional Services* and the
blank form templates (DPW-120, Modified SF330). They are configured as defaults in
[`proposal/config.py`](../../proposal/config.py) (`notice_pdf_path`) and
[`proposal/forms.py`](../../proposal/forms.py) (`default_template`), and can be
overridden per-machine from the dashboard **Settings** dialog.

Keep these here (not in `assets/refs/`, which holds the firm's own example submittals):

| File | Used by |
| --- | --- |
| `Professional-Services-Annual-Ad-Fiscal-Year-2027.pdf` | notice validation + FY2027 DIT skill taxonomy (default) |
| `Professional-Services-Annual-Ad-Fiscal-Year-2026.pdf` | previous-year notice (reference) |
| `DPW-120-fillable.pdf` | DPW-120 form fill |
| `Modified-SF330_Qualification_Form.pdf` | SF330 form (currently flat / not fillable) |
| `DDC Modified Standard Form 330 r6 06.doc` | SF330 source reference |

## Committing

The **binary documents are git-ignored** by the repo-wide `*.pdf` / `*.doc` rules (this
is a public repo — no binaries are committed). Only tracked, text artifacts live here in
git: this README and any derived taxonomy `*.yaml`. A fresh clone therefore has an empty
folder except these text files; drop the reference PDFs back in (or point Settings at
your copies) to use notice validation and form fill.
