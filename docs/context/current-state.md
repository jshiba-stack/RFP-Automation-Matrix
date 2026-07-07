# Current State

> Last reviewed: 2026-07-07 (ProPosal v0.14.0 — Section I classifier + formatting standard + tabbed UI)

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
| ProSE — Professional Services Extractor | v0.2.1 | Scans Hawaii procurement sources (HANDS + HiePRO) for active solicitations matching keywords, records them into a styled Excel sheet with contact details, and emails it on a schedule. Local web dashboard (port 5000). |
| ProPosal — Professional Services Proposal Builder | v0.14.0 | Builds the City & County of Honolulu annual submittal end-to-end. **Import** Sections **I/II/III/IV** from any previous `.docx` into dashboard editors, edit/reorder there, then **Build** syncs content back (append/update with cloned formatting; optional strict rebuild) and **assembles the deliverable PDF** — Word-exported body + each person's one-page resume PDF in Section II order (`<draft> (SUBMITTAL).pdf`), verified page-for-page vs the FY2026 reference. **Section I (professional service categories)** is now managed + **classified against the current-year DIT taxonomy** (`proposal/dit_taxonomy.py` parses the notice's lettered list → `assets/defaults/dit_taxonomy_fy2027.yaml`): `proposal/skills.py` auto-applies exact-name letter matches and flags uncertain/duplicate ones; an optional local-LLM backend (`proposal/llm/`, Ollama, off by default, deterministic fallback) improves fuzzy suggestions. At build, Section I is rebuilt to the house standard — letters reconciled + **uppercased A–X**, sorted, duplicate letters combined (item-deduped), canonical names in col 2, description line breaks preserved; the catch-all **X** keeps per-skill titles under a merged cell. A **document-wide table formatting standard** (`proposal/proofread.py`) runs on every build: font → **12pt**, text colour → **black** (both auto-fixed on every table), borders flagged at **0.5pt single** except **Section III** past-performance tables, which are auto-bordered (full 0.5pt cell grid). **Output name** settable in the build form. Compliance measures the assembled PDF; notice validation; PDF form-fill (DPW-120; SF330 pending fillable template). Fiscal year never silently bumped. UI split into **Build submittal** vs **Forms & other documents** tabs + a **settings/defaults modal**; mandatory reference docs live in `assets/defaults/` (FY2027 notice default). Dashboard port **5001** (ProSE owns 5000). Requires Word (`docx2pdf`). |

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
