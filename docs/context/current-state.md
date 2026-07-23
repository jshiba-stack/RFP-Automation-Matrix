# Current State

> Last reviewed: 2026-07-23 (ProSE v0.5.0 — duplicate-row root cause fixed,
> identical dual contacts collapsed, row auto-fit + conditional top alignment,
> entity decoding, stale-lock failsafe; keyword list refreshed and the workbook
> now lives in a synced SharePoint library)

## Project

- Name: RFP Automation Matrix
- Purpose: A suite of small, focused programs that automate the RFP /
  professional-services procurement workflow — discover relevant solicitations,
  track them, and build the required submittals. Each program is self-contained
  (own folder, README, CHANGELOG, version) and independently runnable, but
  together they form a discover → pursue pipeline.
- Status: Two programs built. **Public** repo (MIT). Bundled example data is
  fictional placeholder only — no firm, personnel, client, or contact details.

## Programs

| Program | Status | Detail |
| --- | --- | --- |
| ProSE — Professional Services Extractor | v0.5.0 | Scans Hawaii procurement sources (HANDS + HiePRO) for active solicitations matching keywords, records them into a styled Excel sheet with contact details, and emails it on a schedule. Local web dashboard (port 5000). A **Keyword** column records which keyword(s) each row matched. **Expired** solicitations (past Due Date, local time) are struck through, greyed, and sorted to the bottom — recomputed every scan. The rewrite **preserves the user's own cell borders + column widths**. **Shared-workbook collaboration:** the workbook path is dashboard-editable so it can live in a **SharePoint/OneDrive-synced** folder shared with a collaborator (ProSE refreshes data columns, collaborator fills action columns, manual columns preserved by Solicitation #); **`shared_workbook`** skips-and-retries a scan when the file is locked (no sibling litter); **`protect_solicitation_column`** locks only column B via Excel sheet protection so the dedup key can't be accidentally edited (openpyxl writes through protection). **Dual HANDS contacts:** captures both the Specifications Contact and the Buyer in one cell (specifications first, consistent across Name/Phone/Email); names normalized to Title Case. When both roles resolve to **the same person** (shared purchasing desk — common on county notices) or only one contact is listed, the contact is written **once with no role tag**; the `(Specifications)`/`(Buyer)` tags appear only when there are genuinely two lines to tell apart. **Rows auto-fit:** every data row's height is computed against the live column widths (`_autofit_row`), the library equivalent of double-clicking the row border — Excel does not auto-fit rows written by a library. Height is measured from **Organization + Contact Name + Email** (`HEIGHT_COLS`), whichever needs the most lines; deliberately not Solicitation Title or Keyword, since fitting a long title makes every row tall and the sheet reads as empty space. Wrapped cells stay vertically **centred** as before, except that a cell whose text is taller than its row switches to **top** alignment (`_overflowing_cols` → `LEFT_WRAP_TOP`/`CENTER_WRAP_TOP`), decided per cell, per scan. Reason: a value taller than its row renders differently per client — desktop Excel anchors overflow to the top (clipping the bottom) while Excel Online/SharePoint honours centring literally and clips top *and* bottom, showing a band through the middle of the letters. Vertical alignment is the only OOXML property that controls this (`shrinkToFit` is ignored when `wrapText` is on), so the fix is conditional rather than a column-wide setting. In practice this is Solicitation Title (never measured for height) plus the occasional Keyword cell on a short row. **HTML entities are decoded**: HANDS returns escaped text (`&#x27;` → `'`, `&#x2F;` → `/`), unescaped in `_strip_html`/`_clean` on the way in and self-healed in ProSE-owned cells of older rows on every merge (never the user's manual columns). Older rows for closed solicitations, which a scan never refreshes, get their doubled same-person contact collapsed in place (`_collapse_repeated_contact`) so historical rows tidy up too. **Dedup hardening:** the HANDS solicitation number is the only key and is never overwritten by a detail fetch (HiePRO renders it as `P27000054 version: 01`, which previously added a fresh row per amendment); HANDS `<span class="highlight">` markup is stripped from *all* fields, not just the title (it can land in the number itself); and on every merge the sheet's own keys are normalized (HTML + `version: NN` suffix stripped, case-folded) so pre-existing duplicate rows **collapse**, with manual values folded in from both copies. **Lock detection** checks Excel's `~$` owner file, not just write permission: a OneDrive/SharePoint co-authored file with AutoSave takes no exclusive OS lock, so the old check silently wrote into an open workbook. `excel_lock_state()` classifies the workbook **free / open / stale** by testing whether any process still holds the workbook *or* its owner file (Windows denies sharing on both while Excel is open); a **stale** owner file — the crash leftover that would otherwise wedge every future scan — is deleted automatically before every write, in both local and shared mode, and reported in the log and banner. Because deletion only ever touches a file no process holds, it can never disarm a live session. **Known limit:** `~$` files are excluded from OneDrive/SharePoint sync, so this guard sees only the *local* Excel session; a remote co-author's open file is not detectable from the filesystem, and the mitigation there stays the off-hours scan schedule plus manual-column preservation on the next merge. All toggles default off. Dashboard port **5000**. |
| ProPosal — Professional Services Proposal Builder | v0.16.1 | Builds the City & County of Honolulu annual submittal end-to-end. **Import** Sections **I/II/III/IV** from any previous `.docx` into dashboard editors, edit/reorder there, then **Build** syncs content back (append/update with cloned formatting; optional strict rebuild) and **assembles the deliverable PDF** — Word-exported body + each person's one-page resume PDF in Section II order (`<draft> (SUBMITTAL).pdf`), verified page-for-page vs the FY2026 reference. Resume picks are **typography-aware**: a newest PDF that a desktop PDF editor re-saved (re-written text layer → stretched glyphs / substituted fonts) yields to a clean same-generation sibling (clean PDF or a `.docx` Word converts cleanly; an *older* clean copy never beats newer content), and every resume PDF merged into the submittal is linted (`pdfutil.resume_pdf_issues`: editor re-save, non-uniformly-scaled text, non-embedded fonts, off-Letter page) with per-person REVIEW flags — a bad source PDF can't silently ship distorted. When a **house resume template** is configured (`resume_template_docx_path`, settings modal; empty = off), a damaged PDF with no clean sibling is **auto-rebuilt** at assembly (`proposal/resume_rebuild.py`): text extracted with layout metadata (pypdf visitor married to plain extraction for word spacing), parsed into name/sections/jobs/bullets, re-typeset onto the template (Title/Heading 1–3/List styles; header+footer come from the template; **current-employer end date normalized to "Present"** via the store's firm names), Word-exported, and gated by a lost-words check — on failure the original merges with flags; on success the rebuilt page merges with a REVIEW proofread flag and a "(REBUILT)" footer tag. Rebuilds are cached under `<output>/resumes_rebuilt/` (git-ignored). Scanner skips `_`-prefixed files (house template lives in the resumes folder as `_...Template....docx`). **Letterhead standard (doc-wide):** the proofread pass normalizes every letterhead-looking page-header line in the draft to **black 9pt, right-aligned with its textbox pinned to the right margin** (block right edge = body text right edge at 540pt; logo-holding paragraphs are excluded — only paragraphs with direct letterhead text are touched) (`proofread.LETTERHEAD_FONT_PT`; pattern-matched — no firm data in code; covers textboxes + mc fallbacks); at assembly, the **body PDF's letterhead block is measured (`pdfutil.letterhead_spec`) and re-set via Word as a position-calibrated stamp** (cached + text-keyed), and **every resume page gets its old header block whited out and the stamp merged on top, shifted down by the page's measured logo offset (`pdfutil.logo_top`, image-XObject Do visitor) so the block sits relative to the logo exactly as the body's does** — one identical letterhead (text/size/color/position) across the whole deliverable. Safety: a resume whose header zone contains non-letterhead text is left untouched and flagged REVIEW. **Section I (professional service categories)** is now managed + **classified against the current-year DIT taxonomy** (`proposal/dit_taxonomy.py` parses the notice's lettered list → `assets/defaults/dit_taxonomy_fy2027.yaml`): `proposal/skills.py` auto-applies exact-name letter matches and flags uncertain/duplicate ones; an optional local-LLM backend (`proposal/llm/`, Ollama, off by default, deterministic fallback) improves fuzzy suggestions. At build, Section I is rebuilt to the house standard — letters reconciled + **uppercased A–X**, sorted, duplicate letters combined (item-deduped), canonical names in col 2, description line breaks preserved; the catch-all **X** keeps per-skill titles under a merged cell. A **document-wide table formatting standard** (`proposal/proofread.py`) runs on every build: font → **12pt**, text colour → **black** (both auto-fixed on every table), borders flagged at **0.5pt single** except **Section III** past-performance tables, which are auto-bordered (full 0.5pt cell grid). **Pagination standard** (same pass): table rows never split across pages (`w:cantSplit`), Section IV always starts a new page, the Appendix divider is a **centered cover page** (own section, `vAlign=center`, jc center, lifted ~2 lines above center via 4 spacer paragraphs; manual page break removed; page numbering continues), TOC entries carry a 0.5″ hanging indent on the `TOC 1` style (uniform text position for wide Roman numerals; dot leaders untouched), and Section III past-performance tables use a 1.5″ label column (wider descriptions → shorter tables). **Submittal size**: `merge_pdfs` deduplicates identical objects across merged parts (stamp fonts, shared logos) — 3.47→2.26 MB on the real build, back under the 3.0 MB cap. **Output name** settable in the build form. Compliance measures the assembled PDF; notice validation; PDF form-fill (DPW-120; SF330 pending fillable template). Fiscal year never silently bumped. UI split into **Build submittal** vs **Forms & other documents** tabs + a **settings/defaults modal**; mandatory reference docs live in `assets/defaults/` (FY2027 notice default). Dashboard port **5001** (ProSE owns 5000). Resume `.docx` conversions strip hyperlink styling and normalize employment dates to “YYYY to YYYY/Present”; PDF-source link-blue text and non-standard date formats are flagged. `pdfutil.export_pdf` drives Word COM directly and **updates fields + TOC before export** (dynamic TOC page numbers; docx2pdf fallback). Requires Word. |

## Stack

- Python; each program has its own `.venv` + `requirements.txt` and a local
  Flask web dashboard (`start.bat` bootstraps).
- ProPosal manipulates Office documents (`.docx`) preserving formatting, fills
  PDF forms, and assembles the deliverable at the PDF level (**requires
  Windows + Word** via `docx2pdf` for the body export / resume conversion);
  sources files from OneDrive/SharePoint-synced folders. See
  [`../decisions/2026-07-04-01-pdf-level-submittal-assembly.md`](../decisions/2026-07-04-01-pdf-level-submittal-assembly.md).
- Git: own repo, remote `jshiba-stack/RFP-Automation-Matrix` (**PUBLIC**, MIT).

## Architectural Boundaries

- Work directly in the existing checkout unless the user explicitly approves
  another workspace.
- Programs are self-contained; the suite root holds only the overview + suite
  milestones. Each program owns its README/CHANGELOG/version.
- **Public repo hygiene:** all business documents (proposals, forms, notices,
  exports) and firm/reference/contact data are git-ignored and must never be
  committed; examples/tests use fictional placeholder data only. See
  [`../decisions/2026-06-30-01-public-repo-privacy-posture.md`](../decisions/2026-06-30-01-public-repo-privacy-posture.md).
- Private working notes (`docs/sessions/`, `docs/audits/`) are git-ignored — this
  matters here because the repo is public.

## Active Concerns

- ProPosal PDF form-fill supports DPW-120; **SF330 is pending a fillable
  template**.
- 2026-07-02 deep review:
  [`../audits/2026-07-02-01-suite-deep-review.md`](../audits/2026-07-02-01-suite-deep-review.md)
  — **all findings remediated same day** (see the audit's Remediation table)
  except ProSE tests, which the user intentionally deleted after they passed
  during development (space saving) and declined to recreate for now.
- Design note exists for a future privacy-preserving local-LLM (Ollama)
  requirements check ([`../../ProPosal/docs/phase6-requirements-llm.md`](../../ProPosal/docs/phase6-requirements-llm.md));
  not yet built.

## Verification Baseline

```text
cd ProPosal  && .venv\Scripts\python -m pytest    # program tests (fictional data)
# ProSE has no tests in-repo: they were written, run, and intentionally
# deleted after passing (user choice, 2026-07-02).
```
