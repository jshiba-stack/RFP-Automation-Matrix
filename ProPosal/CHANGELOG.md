# Changelog

All notable changes to **ProPosal** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.7.0] — 2026-06-30

Phase 6 (part 1): PDF form-fill framework, mirroring the 2a/2b modes.

### Added
- **Form-fill engine (`formfill.py`) + registry (`forms.py`).** Fill a fillable
  PDF AcroForm from the data store, two ways:
  - **generate** — fill a blank template's fields from the store (`forms.FORMS`
    holds each form's default template + a field map; the map is a small demo for
    now, extend as the store gains data);
  - **carry-forward** — seed values from a previously-filled copy (matched by
    field name), then overlay the store, and flag fields that don't line up
    (blank in the new template, or present in the old fill but dropped).
  Flag-only: unmapped/blank fields are reported, never invented.
- **DPW-120** is fillable today (276 named fields). **SF330**'s bundled PDF is
  flat (no form fields) and its Word copy is legacy binary `.doc` — the engine
  detects a non-fillable template and flags it; drop in a fillable SF330 template
  (or override any form's template) to use it.
- `proposal form --type DPW-120 [--template <pdf>] [--store ...] [--prev <pdf>]`
  CLI command and a **"Fill a form (SF330 / DPW-120)"** dashboard card (form
  picker, template override, previous-fill carry-forward) — downloads the filled
  PDF + a flag report.
- Tests for filling from the store, the flat-SF330 flag, and carry-forward.

### Notes
- The DPW-120 field map is intentionally small (framework only). The deferred LLM
  requirements check remains design-only (see `docs/phase6-requirements-llm.md`).

## [0.6.0] — 2026-06-30

Phase 5: validate against the City annual notice (requirements) PDF.

### Added
- **Notice parser + validator (`notice.py`).** Reads the annual ad PDF and
  extracts the fiscal year, submittal email, deadline, attachment/email size
  caps, contract period, and each department's section (service categories +
  required form). `validate()` then flags, against the store:
  - **Fiscal year** mismatch (the notice states the FY on page 1 — so this
    catches validating against the wrong year's ad);
  - **Required form** the department needs but the store lacks (e.g. the notice
    requires SF330 for Design & Construction);
  - **Selected categories** not actually listed for your department (DIT's
    numbered picks are mapped to the notice's lettered sub-items, a→1);
  - **Deadline / size cap / submittal email** surfaced for review.
  All flag-only and clearly worded, since notice parsing is heuristic.
- `proposal validate` CLI command and a **"Validate against the City notice"**
  card on the dashboard. The notice PDF is auto-discovered in your source folder
  (or set explicitly); results render inline as a pass/warn/fail checklist.
- Tests for parsing (FY, caps, deadline, departments, SF330 detection) and
  validation (FY match/mismatch, out-of-range category, missing required form).

## [0.5.0] — 2026-06-30

Renamed the program **ProPose → ProPosal** (folder, `proposal` package, CLI
`python -m proposal`, dashboard, and docs) and added resume cross-verification.

### Added
- **Resumes folder + cross-verification (`resumes.py`).** Attach a folder of
  per-person resume files (often synced from OneDrive/SharePoint). Build and
  generate match it against the data store's `personnel` by name and flag a
  person with no resume on file (REVIEW) or a resume matching nobody (ADD — new
  hire to add?). Generate appends matched `.docx` resumes (PDFs/corrupt files are
  flagged, never crash). Wired through config (`resumes_dir`), the CLI, and the
  dashboard (a "Resumes folder" field with a browse button on both cards; the
  last-used folder is remembered).

### Changed
- All references updated from ProPose/`propose` to ProPosal/`proposal`. Existing
  machine-local config under `instance/` is unaffected.

## [0.4.0] — 2026-06-30

Phase 4: local web dashboard.

### Added
- **Flask dashboard (`app.py`, `templates/dashboard.html`, `static/style.css`).**
  A professional deep-blue / ocean-themed local UI, organized as three steps:
  - **1 · Materials source.** Link one or more named sources (shown as tabs),
    each a local folder. For a **SharePoint** library, click **Sync** /
    **Add shortcut to OneDrive** on it (respects your existing sign-in &
    permissions) and add the resulting local `OneDrive - <Org>` folder; OneDrive
    and plain local folders work identically. Detected locations are offered as
    quick picks, a folder browser navigates like a native "Open" dialog, and the
    path box shows a faded example — but nothing personal is saved or assumed by
    default (no auto-linked folder), so the app is safe to share.
  - **2a · Draft from Version.** Pick the version to update from via a dropdown of
    the `.docx` files discovered in the folder (FINAL/SIGNED/DRAFT auto-labeled),
    choose a data store, set an optional year/date, and build.
  - **2b · Generate from Template / Data Store.** Pick a data store and template
    from the same discovered files, then generate.
  - **3 · Latest result.** Flag report, compliance checklist, and format check
    shown inline with download links. No manual path typing or settings — page
    limit and PDF cap apply automatically.
  - Long actions run in a background worker; the page polls `/status.json`, shows
    a live banner, and refreshes when finished.
- **Folder discovery (`discovery.py`).** Detects OneDrive, scans a folder for
  submittals + data stores (classifying FINAL/SIGNED/DRAFT/template), and powers
  a server-side folder browser (`/api/browse`).
- `proposal dashboard` command (and bare `python -m proposal`) launch the dashboard
  and open a browser; `start.bat` is now a one-click entry point.

## [0.3.0] — 2026-06-30

Phase 3: compliance checklist + format checker.

### Added
- **Compliance checklist (`compliance.py`).** Flag-only checks: all six sections
  + cover letter present, selected categories within the allowed set, exported-PDF
  size ≤ cap (3.0 MB), page count ≤ limit. WARN when it can't verify (no PDF yet);
  FAIL on hard violations.
- **Format checker (`formatcheck.py`).** Confirms formatting survived: running
  footer present, page-number field intact, section headings still use heading
  styles, and (vs a template) no foreign paragraph styles crept in.
- **PDF helpers (`pdfutil.py`).** Measure an exported PDF's size and page count;
  optional Word export (docx2pdf, Windows only) gated by `auto_export_pdf`, for
  measurement only.
- **Shared check model (`checks.py`)** with console + Markdown rendering.
- Both `build` and `generate` now run the checklist + format check automatically
  and write a `*_checks.md` beside the draft. New `proposal check <docx>` command
  runs them standalone (with `--pdf` / `--template`).
- Tests for the checklist (pass / warn-without-pdf / disallowed-category /
  missing-sections) and the format checker.

## [0.2.0] — 2026-06-30

Phase 2: generate-from-data-store, plus a store extractor.

### Added
- **Generate mode (`proposal generate`).** Assembles a fresh draft from a
  template + the data store. The template supplies static prose, logo,
  header/footer, page numbering, and styles; the store rebuilds the data-driven
  tables and the scalars (fiscal year, dates).
  - **Capacity / Project Listing** and **Professional Qualifications** are
    rebuilt row-by-row from `projects` / `personnel`, cloning a model row so cell
    borders/shading/fonts are inherited. Ongoing project end-dates render
    `<cover-year>+`.
  - Resumes listed on `personnel[].resume_docx` are appended via `docxcompose`
    when the files resolve, else flagged `ADD MANUALLY`.
  - Categories, Past Performance, and Additional Criteria are kept from the
    template (reported as template-sourced) pending a later enhancement.
- **Store extractor (`proposal.tools.extract_store`).** Reads the Categories,
  Qualifications, Capacity, and Past-Performance tables out of an existing FINAL
  and writes a complete YAML data store — so you start from real content.
- **Table-building helpers** in `docx_edit.py` (`set_cell_text`,
  `rebuild_table_body`) and reusable scalar edits factored out of `updater.py`
  (`apply_fiscal_year`, `apply_cover_dates`, `apply_ongoing_end_dates`), now
  shared by both modes.
- Tests for extraction round-trip and generate-mode table rebuilds.

## [0.1.0] — 2026-06-30

Initial release: Phase 1, the smart copy-and-update engine.

### Added
- **Smart copy-and-update (`proposal build`).** Opens a previous FINAL submittal
  `.docx` and produces a new draft with the annual-refresh edits auto-applied,
  never mutating the base:
  - Fiscal-year bump in the title block, the inline letter reference, and the
    footer (`FY26` → `FY27`) — leaving the page-number field intact.
  - Cover date and letter date set to the build date.
  - Ongoing Capacity end-dates (`2025+`) refreshed to the current year; completed
    years left as-is.
- **Run-collapse editing helpers (`docx_edit.py`).** Match and rewrite at
  paragraph/cell granularity to survive Word's mid-token run fragmentation
  (`['Fiscal Year 202', '6']`, `['202', '5', '+']`); only the runs a match spans
  are modified, and spans crossing mixed formatting are flagged rather than
  silently collapsed.
- **Structural anchor map (`docx_map.py`).** Locates variable regions by heading
  text, table header-row signatures (Capacity = Client/Project/Start/End), and
  the cover-date region.
- **Data store (`datastore.py`).** Hand-maintained YAML/JSON, multiple sources
  deep-merged by `id`; supplies target fiscal year, cover date, and the entity
  lists used for flagging (and, later, generation).
- **Flag report (`flags.py`).** Every considered edit is either applied (and
  reported) or flagged (`REVIEW` / `ADD MANUALLY` / `UNSAFE EDIT` / `MISSING`);
  written as `*_flags.md` beside each draft.
- **Field-map probe (`tools/inspect_docx.py`)** and a CLI `inspect` command.
- **Tests.** Unit tests for the run-collapse helpers against real fragmentation
  patterns, and an integration test asserting the FY2026 → FY2027 build changes
  exactly the ten intended paragraphs and nothing else.

### Notes
- DIT/general docx format only. SF330 and DPW-120 form-filling are deferred; the
  data-store schema is designed to feed them later.
- Generate-from-data-store, compliance checks, the dashboard, and notice
  validation are planned for Phases 2–5 (see the README roadmap).
