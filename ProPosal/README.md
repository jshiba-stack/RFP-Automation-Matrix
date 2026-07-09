# ProPosal — Professional Services Proposal Builder

The second program in the **RFP Automation Matrix** suite. Where
[ProSE](../ProSE/) *discovers* opportunities, ProPosal helps you *respond* to the
City & County of Honolulu annual Professional Services submittal — a
frozen-format document you refresh once a year rather than write from scratch.

## What it does

The annual submittal's structure never changes (Cover Letter → Categories →
Professional Qualifications → Past Performance → Capacity / Project Listing →
Additional Criteria → Resumes). Only a handful of fields move year to year. So
ProPosal has two modes:

1. **Smart copy-and-update (primary).** Open last year's FINAL `.docx`,
   auto-apply the mechanical edits, and **flag** everything else for your
   review. The base file is never touched — you get a new draft plus a report.
   Auto-applied edits:
   - Fiscal year bump (`Fiscal Year 2026` → `2027`, the inline letter reference,
     and the footer `FY26` → `FY27` — without disturbing the page-number field).
   - Cover date and letter date → the build date.
   - Ongoing Capacity end-dates (`2025+`) → the current year (`2026+`). Completed
     years (`2024`) are left alone.
2. **Generate-from-data-store (secondary).** Assemble a fresh `.docx` from a
   template + the data store: the template supplies the static prose, logo,
   header/footer, and styles; the store rebuilds the data-driven tables
   (Capacity / Project Listing and Professional Qualifications) and the scalars.
   Bootstrap a complete store from an existing FINAL with the extractor.

Both read a hand-maintained **data store** (`data/stores/*.yaml`) — the single
source of truth for firm info, categories, personnel, projects, and references.
It also feeds the **DPW-120** form-filler (and the deferred **SF330**).

Beyond the two build modes, ProPosal **assembles the deliverable PDF** the way
the real submittals are put together — the Word-exported body followed by each
person's one-page resume PDF in Section II order — and enforces a set of
document-wide standards on every build so the output ships clean:

- **Section I classification.** Categories are reconciled against the
  current-year DIT taxonomy (parsed from the annual notice), letters self-heal,
  and the section is rebuilt to the house standard (uppercased `A–X`, sorted,
  duplicates merged, canonical names). Uncertain matches are flagged, never
  silently applied. An optional local LLM (Ollama, off by default) sharpens the
  fuzzy suggestions; a deterministic scorer runs otherwise.
- **Table, pagination & letterhead standards.** Every table is normalized to
  12pt / black with 0.5pt borders; rows never split across pages; Section IV
  starts a new page; the Appendix gets a centered cover page; the table of
  contents regenerates with correct page numbers; and one identical letterhead
  block (black, 9pt, right-aligned) is stamped across every page — body and
  resume pages alike.
- **Resume typography.** Every resume PDF merged in is linted for distortion
  (a desktop PDF editor re-saving a file can stretch glyphs and drop embedded
  fonts). A clean same-generation sibling is preferred automatically; if a
  house resume template is configured, a damaged page with no clean sibling is
  re-typeset onto it (gated by a lost-words check) rather than shipping
  distorted.
- **Compliance & validation.** A compliance checklist (measured against the
  assembled PDF — size ≤ 3.0 MB, page limit, required sections) and a format
  check run on every build, and the store can be validated against the City's
  annual notice PDF.

> Why not a naive find/replace? Word splits values across runs — `"Fiscal Year
> 2026"` is stored as `['Fiscal Year 202', '6']` and an end-date as
> `['202', '5', '+']`. ProPosal matches and rewrites at paragraph/cell
> granularity, touching only the runs a match actually spans, so formatting and
> fields survive.

## Quick start

The easiest way in is the **local dashboard** — double-click `start.bat` (it
creates the venv on first run and opens your browser), or:

```bash
cd ProPosal
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m proposal            # launches the dashboard
```

In the dashboard you (1) link a **materials source** — a SharePoint library you've
**Synced** to a local folder (via *Add shortcut to OneDrive*, which respects your
sign-in), your OneDrive, or any local folder; add as many as you like and switch
between them as tabs. ProPosal then discovers your past submittals and data stores
and offers them as dropdowns. Step (2) maintains your **submittal content** in the
data store with forms that mirror the proposal's own tables — (2a) Personnel &
Resumes with the resume folder cross-reference, (2b) Past Performance blocks,
(2c) the Capacity project listing — each with edit / delete / reorder on existing
entries. Step (3) builds the draft **and assembles the submittal PDF**: pick any
starting document (previous version or template), ProPosal syncs your step-2
content into it, exports the body to PDF via Word, and merges each person's
one-page resume PDF after it in Section II order — exactly how the real
submittals are put together (resumes never live in the .docx). Step (4) checks &
forms — (4a) validate against the City's annual notice PDF, (4b) fill a PDF form
(DPW-120/SF330). Step (5) shows the flag report, compliance checklist (measured
against the assembled PDF), and format check inline with download links. Fiscal
year and dates update automatically (override under *Advanced*); no path typing,
and nothing is linked automatically.

> **SharePoint:** ProPosal reads files from a local folder, so sync the library
> first (open it in the browser → **Sync** / **Add shortcut to OneDrive**). It
> appears under `OneDrive - <Org>` and stays in sync using your existing account.

Prefer the command line?

```bash
# 1) point a data store at your firm/opportunity details
copy docs\data_store.example.yaml data\stores\store.yaml   # then edit it

# 2) build next year's draft from last year's FINAL
.venv\Scripts\python -m proposal build ^
    --base "assets\refs\Your Previous Submittal (FINAL).docx" ^
    --store data\stores\store.yaml

# the draft + flag and checks reports land in data\output\
```

Flags / overrides:

- `--fy 2027` — target fiscal year (default: the store's
  `opportunity.fiscal_year`, else the document keeps its own year).
- `--date "2026-03-02"` — cover date (default: today, or the store's
  `opportunity.cover_date`).
- `--store` is repeatable; stores are deep-merged in order (a stable `firm.yaml`
  plus a per-year `opportunity_FY2027.yaml`, one possibly in OneDrive).

Generate a fresh draft from a template + data store:

```bash
# bootstrap a complete store from last year's FINAL (one time)
.venv\Scripts\python -m proposal.tools.extract_store ^
    "assets\refs\Your Previous Submittal (FINAL).docx" ^
    -o data\stores\store.yaml

# assemble a new draft (rebuilds Capacity + Qualifications from the store)
.venv\Scripts\python -m proposal generate --store data\stores\store.yaml --fy 2027
```

Both `build` and `generate` run the compliance checklist + format check
automatically and write a `*_checks.md` beside the draft. To check a document on
its own (measuring an exported PDF for size/page limits):

```bash
.venv\Scripts\python -m proposal check "data\output\draft.docx" ^
    --store data\stores\store.yaml --pdf "data\output\draft.pdf"
```

Validate your store against the City's annual notice (requirements) PDF:

```bash
.venv\Scripts\python -m proposal validate --store data\stores\store.yaml ^
    --notice "assets\refs\Professional-Services-Annual-Ad-Fiscal-Year-2026.pdf" --fy 2026
```

Inspect a document's structure (the field-map probe):

```bash
.venv\Scripts\python -m proposal inspect "path\to.docx" --runs
```

## How it works

| Module | Role |
|--------|------|
| `proposal/docx_edit.py` | Run-collapse replace helpers (match/rewrite at paragraph/cell level; preserve untouched runs and fields; flag mixed-formatting spans). |
| `proposal/docx_map.py` | Structural anchors — headings, table header-row signatures, cover-date region, fiscal-year and footer patterns. |
| `proposal/updater.py` | Primary mode: apply the mechanical edits, flag the rest. |
| `proposal/generator.py` | Secondary mode: rebuild data-driven tables from the store, inherit static prose/styles from the template. |
| `proposal/datastore.py` | Load + deep-merge YAML/JSON stores (lists merge by `id`). |
| `proposal/storewrite.py` | Comment-preserving store writer: append / update / delete / reorder records via YAML text-splice (JSON too). |
| `proposal/skills.py` | Section I classifier: reconcile categories against the DIT taxonomy, finalize to the house standard (uppercase A–X, dedup, merged X). |
| `proposal/dit_taxonomy.py` | Parse the notice's lettered `A.`–`X.` DIT list; cache to `assets/defaults/`. |
| `proposal/llm/` | Pluggable local-LLM backend (Ollama over stdlib `urllib`), off by default; deterministic fallback otherwise. |
| `proposal/proofread.py` | Document-wide standards pass: table font/colour/borders, pagination (`w:cantSplit`, section breaks, appendix cover), TOC indent, letterhead normalization. |
| `proposal/compliance.py` | Practical checklist: sections, category subset, PDF size, page limit (measured on the assembled PDF). |
| `proposal/formatcheck.py` | Format check: footer, page-number field, heading styles, foreign styles, table consistency. |
| `proposal/pdfutil.py` | Measure/export PDFs via Word COM (fields + TOC updated before export); resume typography lint; letterhead spec/stamp/logo detection; dedup merge. |
| `proposal/resumes.py` | Cross-verify `personnel` against the resumes folder; typography-aware resume picking; append/merge matched resumes. |
| `proposal/resume_rebuild.py` | Re-typeset a damaged resume PDF onto the house template (parse → render → lost-words gate); "Present" employment rule. |
| `proposal/tools/extract_store.py` | Bootstrap a complete data store from an existing FINAL (Sections I/II/III/IV). |
| `proposal/flags.py` | Change/flag records + console and Markdown reports. |
| `proposal/config.py` | `instance/config.json` settings + runtime state (adapted from ProSE). |
| `proposal/jobs.py` | Orchestration shared by the CLI and the dashboard. |
| `proposal/app.py` + `templates/` + `static/` | Local Flask dashboard (ocean-blue theme, tabbed UI + settings modal). |
| `proposal/discovery.py` | Detect OneDrive/SharePoint syncs, scan a folder for submittals/stores, folder browser. |
| `proposal/notice.py` | Parse the City annual notice PDF; validate FY, categories, required form, deadline. |
| `proposal/formfill.py` + `forms.py` | Fill a fillable PDF form (DPW-120) from the data store; carry forward a previous fill. |
| `proposal/tools/inspect_docx.py` | Read-only Phase-0 probe used to build the field map. |

## Roadmap

- **Phase 1 — Smart copy-and-update.** ✅ Done.
- **Phase 2 — Generate-from-data-store** (+ store extractor). ✅ Done. Capacity
  and Qualifications are store-driven; Categories and Past Performance are still
  template-sourced (their rich multi-paragraph cells are a future enhancement).
- **Phase 3 — Compliance + format check.** ✅ Done. Practical checklist
  (required sections, category subset, PDF size ≤ 3.0 MB, page limit) and a
  format checker (footer, page-number field, heading styles, foreign styles).
  Both run automatically after build/generate; also `proposal check` standalone.
- **Phase 4 — Local web dashboard.** ✅ Done. Ocean-blue Flask UI: pick
  base/template + store, build or generate, and review flags + checks inline with
  downloads; long actions run in the background with live status.
- **Phase 5 — Notice validation.** ✅ Done. Parse the annual ad PDF and validate
  the store against it (fiscal year, required form, selected categories, deadline,
  size cap) — flag-only, run from the dashboard or `proposal validate`.
- **Phase 6 — Form-fillers.** 🚧 Framework done. Fill a fillable PDF form from the
  data store (generate) or carry a previous fill forward, flag-only. **DPW-120**
  works now; **SF330**'s bundled PDF is flat (provide a fillable template to use
  it). The field map is a small demo — extend as the store gains data. The
  optional LLM requirements check is design-only (`docs/phase6-requirements-llm.md`).

Beyond the original six phases, later releases turned ProPosal into a full
end-to-end submittal builder (see `CHANGELOG.md` for detail):

- **Content round-trip & entry management** (v0.8–v0.11). Capture and
  **import** Sections I/II/III/IV from a previous `.docx` into the dashboard
  editors (edit / delete / reorder, comment-preserving), then Build **syncs
  content back** into the document — appending or updating in place with cloned
  formatting, never deleting.
- **PDF-level submittal assembly** (v0.12). The deliverable is assembled at the
  PDF level: Word-exported body + each person's one-page resume PDF in Section II
  order → `<draft> (SUBMITTAL).pdf`, verified page-for-page against the reference.
- **Proofread / formatting standards** (v0.13–v0.14, v0.16). Output file naming,
  a document-wide table standard (12pt / black / 0.5pt borders), and a pagination
  standard (no split rows, Section IV page break, appendix cover page, live TOC).
- **Section I DIT classifier** (v0.14). Reconcile categories against the
  current-year taxonomy and rebuild Section I to the house standard; optional
  local LLM, deterministic fallback. Tabbed UI + settings modal.
- **Resume standardization** (v0.15–v0.16). Typography lint + typography-aware
  picking, auto-rebuild of damaged resumes onto a house template, a document-wide
  letterhead standard, link-colour and employment-date standards, and PDF size
  deduplication.

## Notes & limits

- Only **Word** renders the submittal faithfully — export the final PDF from
  Word. ProPosal can optionally measure that PDF (size / page count) for the
  compliance checklist; it does not produce the deliverable PDF itself.
- The Table of Contents page numbers go stale after edits — let Word update
  fields on open / PDF export.
- Business content (reference proposals under `assets/refs/`, your data stores
  under `data/`, and `instance/`) is git-ignored and never committed.
