# Current State

> Last reviewed: 2026-07-04 (ProPosal v0.13.0 — output-name control + table proofread)

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
| ProSE — Professional Services Extractor | v0.3.0 | Scans Hawaii procurement sources (HANDS + HiePRO) for active solicitations matching keywords, records them into a styled Excel sheet with contact details, and emails it on a schedule. Local web dashboard (port 5000). |
| ProPosal — Professional Services Proposal Builder | v0.13.0 | Builds the City & County of Honolulu annual submittal end-to-end: **import** Sections II/III/IV from any previous `.docx` into dashboard editors, edit/reorder there, then **Build (3)** syncs content back into the chosen starting document (append/update with cloned formatting; optional strict rebuild) and **assembles the deliverable PDF** — Word-exported body + each person's one-page resume PDF in Section II order (`<draft> (SUBMITTAL).pdf`), verified page-for-page against the FY2026 reference. Resume picking: newest one-page .pdf per person (folder-per-person layouts understood; full-name beats surname). **Output name** is settable in the build form (blank = default `Professional Services Submittal FY…_DRAFT_<date>` stem). A **table proofread pass** (`proposal/proofread.py`) runs before save: normalizes each body table's data rows to its dominant font size and gives sibling Past-Performance blocks a consistent interior border — auto-fixed, recorded under Applied changes, and REVIEW-flagged for the human. Compliance measures the assembled PDF; notice validation; PDF form-fill (DPW-120; SF330 pending fillable template). Fiscal year never silently bumped. Dashboard port **5001** (ProSE owns 5000): 1 source → 2 import + content managers → 3 build+assemble → 4 checks/forms → 5 results (flags in per-kind subtabs with persisted review checkboxes). Requires Word (`docx2pdf`). |

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
