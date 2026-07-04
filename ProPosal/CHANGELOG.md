# Changelog

All notable changes to **ProPosal** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.12.0] — 2026-07-02

The submittal is assembled the way the real ones are: at the PDF level.
Verified page-for-page against the FY2026 DRAFT PDF (21/21 pages, all ten
resume pages identical people in identical order).

### Changed
- **Resumes are merged as PDF pages, not docx content.** Inspecting the
  references showed the truth: every draft/FINAL `.docx` ends at the
  "Appendix: Resumes of Key Personnel" heading, and the deliverable PDF's
  resume pages are each person's own **PDF export** (their `CONFIDENTIAL …
  1P` footers). The docxcompose append (which restyled resumes with the
  proposal's own style definitions — the "formatting looks off" bug) is gone.
  Build now: exports the body PDF via Word (`docx2pdf`, COM-initialized for
  worker threads), converts any `.docx` resume picks to PDF, and merges
  `body + resume pages` in Section II order into
  `<draft> (SUBMITTAL).pdf` — downloadable from step 5.
- **Resume picking prefers the newest one-page .pdf** (that *is* the page
  that ships), then a one-page `.docx` (converted at build time), then any
  newest one-pager, then newest overall.
- **Cards 3a/3b merged into one "3 · Build the draft & submittal PDF"** —
  one starting-document picker (previous version or template), with a
  *strict rebuild* checkbox under Advanced replacing generate mode (Sections
  II/IV rebuilt purely from the store vs. synced in place). The CLI keeps
  `build` and `generate`.
- The compliance PDF size / page-limit checks now measure the **assembled
  submittal** (the actual attachment), not a body-only export.
- Requirements: `docx2pdf` is now required (Windows + Word); `docxcompose`
  dropped.

## [0.11.0] — 2026-07-02

Section III sync lands in Generate too; resumes append one-per-page with a
.docx preference; the review surfaces stop drowning in per-file noise.

### Added
- **Generate (3b) now syncs Past Performance from the store** (same engine as
  3a): existing blocks keep their formatting and get changed fields updated;
  new engagements get a cloned block. "Kept from template" no longer applies
  to Section III.
- **Flags to review: per-category subtabs with a review checklist.** Flags
  group into collapsible sections by kind (first one open), each row has a
  "reviewed" checkbox — ticked rows dim/strike and the group header counts
  "n of m reviewed"; checkmarks persist (localStorage) until a new build.

### Changed
- **Resume picking prefers a one-page `.docx`** over a newer one-page PDF —
  only `.docx` can be merged into the proposal. Real-folder result went from
  4 appendable picks to 9 of 10.
- **Resumes append one per page**: a page break precedes each appended resume
  (matching how the FINAL lays them out) instead of running on.
- **Cross-reference panel decluttered**: matched people live in a collapsed
  "n matched — expand to review" section; orphan files collapse to **one line
  per person-folder** with a file count; the alternates wall is gone (a count
  remains inside the matched section). Build/generate flag reports likewise
  emit one orphan flag per folder, not per file (27 flags → 3 on real data).

### Fixed
- **Project-less Past Performance store records** (old extractor format) no
  longer append a duplicate block when their client already has several
  engagements — they match the first existing block instead. (Named-project
  records still append when that engagement is genuinely new.)

## [0.10.0] — 2026-07-02

Build (3a) now carries your content into the document, and the document's own
content can be imported into the editors — a full round-trip.

### Added
- **Store sync in Draft from Version (3a).** Step-2 content is applied to the
  base document instead of just flagged: new **Section IV** rows and
  **Section II** resource rows are appended by cloning an existing row's
  formatting; new **Section III** engagements get a whole cloned block (6-row
  table + the lettered client paragraph, whose list numbering continues
  automatically); matched entries get changed fields **updated in place**
  (by row label for Section III, so layout variations are tolerated). Every
  change is reported; nothing in the document is ever deleted. Backed by
  `updater.apply_store_sync` + `docx_edit.append_cloned_row`.
- **Import from a previous submittal (new step-2 card).** Pick any discovered
  `.docx` and its Sections II / III / IV are extracted into
  `store_imported.yaml` in your source, appearing immediately in the step-2
  editors — edit, reorder, delete there, then Build re-applies them.
  Re-importing overwrites the imported file (confirm prompt; dashboard edits
  to it included). The extractor now pulls **full Past Performance blocks**
  (project / contact / phone / scope / issue resolution, matched by row
  label), with unique ids even when one client has several engagements.

### Fixed
- **Per-person resume subfolders are now understood.** The scanner previously
  looked only at files directly inside the resumes folder and matched only by
  file name — a layout like `Jordan Avery\Resume 2024.docx` matched nobody, so
  every person showed "no resume file found". Scanning is now recursive
  (skipping `~$`/hidden entries) and a containing **folder name identifies the
  person** too; the cross-ref panel shows folder-relative paths. Matching is
  also tiered — a **full-name** match always beats a last-name-only match — so
  people sharing a surname can't steal each other's folders.
  Verified against the real folder: every person matched, each to their own
  one-page profile file.

### Changed
- **No more "detected + 1" fiscal-year default.** The document keeps its own
  fiscal year unless the store's `opportunity.fiscal_year` or an explicit
  override says otherwise (building from a current-year draft no longer
  silently bumps to next year). When target equals the detected year, nothing
  is rewritten.

### Verification
- 65/65 tests (5 new sync tests, extractor test); the user's exact failed
  scenario (test entries + FY2027 draft) reproduced live: entries land in the
  document, FY stays 2027, zero flags.

## [0.9.0] — 2026-07-02

Content-first dashboard: Section II manager + resume cross-reference, full
entry management (edit / delete / reorder), and a logical 1→5 reorganization.

### Added
- **Personnel & Resumes card (2a) — Section II manager.** A form mirroring the
  Professional Qualifications table (Resource / Qualifications) plus a numbered
  list of current resources in **append order** with ↑↓ / edit / delete. The
  resumes folder now lives here too ("Save & check"): the card cross-references
  personnel against the folder inline — matched files in append order, people
  with no resume, and orphan resumes that match nobody — with the caveats
  spelled out (only `.docx` can be merged; name matching is fuzzy).
- **View / edit / delete / reorder for all entry types.** Each content card
  (II, III, IV) lists its current store entries. ✎ loads the entry back into
  the form ("Update … — <id>", cancel restores), × deletes (with confirm),
  ↑↓ reorders — all comment-preserving via new `storewrite.update_record`,
  `delete_record`, `move_record` (YAML text-splice + JSON; validated before
  write; emptied lists become `key: []`, never a null key). 6 new tests.
- Capacity form cells are now wrapping textareas, so long client/project
  titles fit and grow vertically.
- **Multi-file resume folders are handled.** When several files match one
  person (long + one-page versions, old drafts), ProPosal picks the **newest
  one-page** file — page count read via pypdf (.pdf) or Word's
  `docProps/app.xml` (.docx) — falling back to the newest overall when no
  one-pager exists (that uncertain pick is flagged REVIEW in builds). The
  losing copies are reported as "alternates", not "new hire?" orphans, and the
  cross-reference panel shows which copy won and why. Heuristic is
  intentionally simple and easy to swap later.

### Changed
- **Dashboard reorganized around the workflow:** 1 materials source →
  2 submittal content (2a Personnel & Resumes, 2b Past Performance,
  2c Capacity) → 3 build (3a Draft from Version, 3b Generate) → 4 checks &
  forms (4a validate vs notice, 4b fill a form) → 5 latest result.
- Entry buttons renamed to **"Commit new Section II/III/IV …"** and unified to
  one color (primary).
- The resumes folder is configured once in card 2a; 3a/3b use it automatically
  (their per-form resumes field is gone).

### Fixed
- Textarea placeholder text (Scope / Issue Resolution) now matches the input
  placeholder color — the CSS only styled `input::placeholder`.

## [0.8.0] — 2026-07-02

Project-entry capture for Sections III & IV, plus review fixes.

### Added
- **"Add a project entry" dashboard card (2e).** Two forms styled to mirror the
  submittal's own tables — a Section III **Past Performance** block (Client /
  Project / Client Contact / Client Phone / Detailed Scope of Work / Issue
  Resolution) and a Section IV **Capacity / Project Listing** row (Client /
  Project / Start Date / End Date) — with grayed example text in every box.
  Entries append to a chosen data store (or a new `store_additions.yaml` in the
  active source); Generate (2b) then rebuilds Section IV from `projects`, and
  Build (2a) flags new Section III clients to add manually.
- **Comment-preserving store writer (`storewrite.py`).** Appends a record to a
  top-level list (`projects` / `past_performance`) by splicing text into the
  YAML block — comments, ordering, and spacing survive. Generates unique ids,
  re-parses before writing (atomic replace; never writes a broken store), and
  handles missing files/keys, inline `[]`, and JSON stores. Tested.
- `past_performance` records may now carry `project`, `contact`, `phone`,
  `scope`, and `issue_resolution` alongside `client` (captured for the future
  store-driven Past Performance rebuild).

### Changed
- **Dashboard decluttered around the automation.** Fiscal year, cover date,
  data-store choice, and resumes folder are override fields — everything runs
  automatically without them (detected year + 1, today's date, the discovered
  store). They now live in a collapsed **Advanced** panel on 2a/2b/2c, the
  first discovered store is pre-selected everywhere, and card 2e's
  "save into" is automatic when there's only one sensible target (single
  store, or a new `store_additions.yaml` when none exists).
- **Dashboard default port is now 5001** (ProSE owns 5000), so both dashboards
  can run at the same time.

### Fixed
- **Compliance check #2 no longer false-FAILs valid stores.** The offline
  "allowed set" is now only the explicit `opportunity.allowed_categories`; the
  store's *descriptive* `categories` list (often partial) is no longer treated
  as authoritative — without an explicit set the check WARNs and points at
  notice validation (2c). A separate soft WARN lists selected categories that
  have no Section-I description.
- **Notice validation now FAILs a passed deadline** ("is this last year's
  notice?") instead of always warning.
- Client/project matching (`updater._flag_new_entities`) now normalizes commas
  and newlines, so a store client written `City & County of Honolulu,
  Department of ...` matches the doc's two-line block header instead of raising
  a false ADD-MANUALLY flag.
- Heading checks (compliance + format) no longer accept prose that merely
  mentions a heading's text: a heading counts if a Heading/Title-styled
  paragraph contains it or a paragraph starts with it — and the format check
  prefers the styled paragraph, so body text can't trigger a false
  `style='Normal'` FAIL.
- The form-fill flag report is downloadable even when no PDF was produced
  (flat template) — previously the link was dropped exactly when the report
  mattered most.
- A run-fragmented match starting at an *empty* run no longer risks a spurious
  UNSAFE-EDIT flag (empty runs render nothing; their formatting is ignored in
  the uniformity check).
- Config/state writes are atomic (temp file + `os.replace`).

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
