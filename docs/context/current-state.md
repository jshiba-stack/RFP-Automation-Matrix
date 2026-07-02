# Current State

> Last reviewed: 2026-07-02

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
| ProSE — Professional Services Extractor | v0.2.0 | Scans Hawaii procurement sources (HANDS + HiePRO) for active solicitations matching keywords, records them into a styled Excel sheet with contact details, and emails it on a schedule. Local web dashboard. |
| ProPosal — Professional Services Proposal Builder | v0.7.0 | Builds the City & County of Honolulu annual submittal. Two modes: refresh last year's FINAL `.docx` (auto-update variable fields, flag the rest) or generate from a data store (rebuild Capacity/Qualifications tables) — preserving formatting. Compliance checklist + format check on every draft; local dashboard; resume cross-verification; validation against the annual notice PDF; PDF form-fill (DPW-120 today; SF330 pending a fillable template). |

## Stack

- Python; each program has its own `.venv` + `requirements.txt` and a local
  Flask web dashboard (`start.bat` bootstraps).
- ProPosal manipulates Office documents (`.docx`) preserving formatting, and
  fills PDF forms; sources files from OneDrive/SharePoint-synced folders.
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
- Design note exists for a future privacy-preserving local-LLM (Ollama)
  requirements check ([`../../ProPosal/docs/phase6-requirements-llm.md`](../../ProPosal/docs/phase6-requirements-llm.md));
  not yet built.

## Verification Baseline

```text
cd ProSE     && .venv\Scripts\python -m pytest    # program tests
cd ProPosal  && .venv\Scripts\python -m pytest    # program tests (fictional data)
```
