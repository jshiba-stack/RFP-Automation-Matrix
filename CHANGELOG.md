# Changelog — RFP Automation Matrix

Suite-level milestones (programs added, retired, or significantly changed).
Each program keeps its own detailed changelog in its folder.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## 2026-07-08

### Changed
- **ProPosal v0.14.0 → v0.15.0** — resume pages become standardized
  deliverables; see [ProPosal/CHANGELOG.md](ProPosal/CHANGELOG.md):
  - **Root cause found for the "stretched resume" mystery**: source PDFs
    re-saved by a desktop PDF editor draw text up to 33% taller than designed
    and leave fonts un-embedded; the assembly merge was never at fault.
  - **Typography lint** on every merged resume PDF (editor re-save, stretched
    text, non-embedded fonts, off-Letter page → per-person REVIEW flags) and a
    **typography-aware picker** (a clean same-generation sibling replaces an
    editor-mangled newest pick; freshness always beats typography).
  - **Auto-rebuild** (`proposal/resume_rebuild.py`): a damaged resume PDF with
    no clean sibling is re-typeset onto the house template at assembly —
    extract (word-spacing restoration) → parse → render → Word export → gated
    by a lost-words check; never silent (REVIEW flag + "(REBUILT)" footer tag).
    Includes the **"Present" rule** for the current employer's end date.
  - **Letterhead standard, document-wide**: black 9pt, right edge flush with
    the content margin, position matched to each page's logo — the body's
    letterhead is measured and restamped over every resume page's drifting
    copy, so the whole deliverable carries one identical firm block.
  - Suite at 118 tests (21 new, fictional data).

## 2026-07-07

### Changed
- **ProPosal v0.13.0 → v0.14.0** — Section I (professional service categories)
  becomes a managed, self-standardizing section, plus a document-wide table
  formatting standard and a tabbed UI; see
  [ProPosal/CHANGELOG.md](ProPosal/CHANGELOG.md):
  - **Section I skill classification.** New taxonomy parser
    (`proposal/dit_taxonomy.py`) reads the annual notice's lettered DIT list; a
    classifier (`proposal/skills.py`) reconciles each skill against it —
    exact-name matches auto-apply the correct letter, everything uncertain or
    duplicated is flagged. Optional local-LLM backend (`proposal/llm/`, Ollama,
    off by default with a deterministic fallback) sharpens the fuzzy suggestions.
    A dashboard card extracts/edits categories with **Classify**, **Accept**, and
    **Accept all**.
  - **Section I rebuilt to house standard at build**: letters reconciled and
    uppercased A–X, sorted, duplicate letters combined with item-level
    de-duplication, canonical names in column 2, description line breaks
    preserved; the catch-all **X** keeps per-skill titles under a merged cell.
  - **Table formatting standard** (`proposal/proofread.py`, rewritten): every
    table auto-fixed to 12pt / black text; borders flagged at 0.5pt except
    Section III past-performance tables, which are auto-bordered.
  - **UI**: dashboard split into Build vs Forms tabs; a settings/defaults modal;
    a mandatory-documents folder (`assets/defaults/`, FY2027 notice default).
  - **Fixes**: category-id collision (unlettered rows collided → keyed off name
    now), scroll-to-top on every edit, smashed multi-line descriptions, and
    stale cross-session classification state.

## 2026-07-04

### Changed
- **ProPosal v0.12.0 → v0.13.0** — output-file-name control and a table
  proofread pass; see [ProPosal/CHANGELOG.md](ProPosal/CHANGELOG.md):
  - **Name the deliverable**: an optional *Output file name* box in the build
    form names the `.docx`, the `… (SUBMITTAL).pdf`, and the reports (blank =
    the default dated stem; input is sanitized). Firm-standard default still TBD.
  - **Table proofread on every build** (`proposal/proofread.py`): each body
    table's data rows are normalized to that table's dominant font size, and
    sibling Past-Performance blocks are reconciled to a consistent interior
    border — auto-fixed, recorded under Applied changes, and REVIEW-flagged for
    human verification. The format check now also reports table font/border
    consistency.
- **ProPosal v0.7.0 → v0.12.0** — five releases in one extended session; see
  [ProPosal/CHANGELOG.md](ProPosal/CHANGELOG.md) for detail:
  - **Submittal assembled at the PDF level** (the way the real ones are built):
    Build exports the body via Word and merges each person's one-page resume
    PDF after it in Section II order → `<draft> (SUBMITTAL).pdf`, verified
    page-for-page against the FY2026 reference (21/21 pages, all ten resume
    pages identical). Resumes never live in the `.docx`; docxcompose dropped,
    `docx2pdf` now required.
  - **Content round-trip**: import Sections II/III/IV from any previous
    submittal into dashboard editors (comment-preserving `storewrite.py` —
    append/edit/delete/reorder), then Build syncs them back into the document
    (new rows/blocks appended with cloned formatting, changed fields updated).
  - **Dashboard reorganized** (source → content managers → one Build card with
    a strict-rebuild option → checks/forms → results with per-kind flag
    subtabs + persisted review checkboxes); port moved to 5001 so ProSE (5000)
    can run alongside; fiscal year is never silently bumped anymore.
  - **Resume intelligence**: per-person subfolders understood, full-name
    matches beat shared surnames, newest one-page PDF preferred per person.
- **ProSE v0.2.0 → v0.2.1** — robustness fixes from the suite deep review
  (patch: fixes only):
  Excel-locked workbooks divert to a timestamped file instead of losing the
  scan, duplicate solicitation rows collapse, `schtasks` failures surface,
  atomic config/state writes. See [ProSE/CHANGELOG.md](ProSE/CHANGELOG.md).
- **Suite deep review (2026-07-02)** — full audit of both programs; all
  findings remediated same day (High: a compliance-checklist false-FAIL).
  Findings + remediation table live in the private audit notes.

## 2026-07-02

### Added
- **Adopted the tool-neutral `docs/` memory framework** at the suite root
  (context / decisions / plans / sessions / audits / runbooks + a context-contract
  and `CLAUDE.md`/`AGENTS.md` entry points). Authored a rich
  `docs/context/current-state.md` and three decision records (program-suite
  structure, public-repo privacy posture, ProPosal dual-mode build). Working notes
  (`docs/sessions/`, `docs/audits/`) are git-ignored — important since this repo is
  public. `docs/` complements this changelog; it does not replace it.

## 2026-06-30

### Added
- **ProPosal** (Professional Services Proposal Builder) **v0.7.0** — the second
  program in the suite. Builds the City & County of Honolulu annual submittal:
  smart copy-and-update from last year's FINAL, generate-from-data-store (with a
  store extractor), an automatic compliance checklist + format checker, an
  ocean-blue local dashboard sourcing files from OneDrive/SharePoint-synced
  folders, resume cross-verification, validation against the annual notice PDF,
  and a PDF form-fill framework (DPW-120 today; SF330 pending a fillable
  template). See [ProPosal/CHANGELOG.md](ProPosal/CHANGELOG.md).
- Design note for a future, privacy-preserving local-LLM (Ollama) requirements
  check ([ProPosal/docs/phase6-requirements-llm.md](ProPosal/docs/phase6-requirements-llm.md)).

### Changed
- Hardened the root `.gitignore` to keep all business documents (proposals,
  forms, notices, exports) and firm/reference data out of the public repo. The
  bundled example data store and tests use **fictional placeholder data only** —
  no firm, personnel, client, or contact details.

## 2026-06-27

### Added
- **ProSE** (Professional Services Extractor) **v0.1.0** — scans Hawaii
  procurement sources (HANDS + HiePRO) for active solicitations, extracts full
  contact details into a styled Excel spreadsheet, and emails it on a schedule
  via a local dashboard. See [ProSE/CHANGELOG.md](ProSE/CHANGELOG.md).
- Established the suite structure and conventions (one folder per program; each
  with its own README, CHANGELOG, and version; secrets and generated data kept
  local and never committed).
