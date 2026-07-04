# Decision: Assemble the submittal deliverable at the PDF level

> Date: 2026-07-04
> Status: accepted
> Supersedes: none
> Superseded by: none

## Context

The submittal's Appendix must contain one formatted resume page per person in
Section II order. ProPosal initially merged resume `.docx` files into the
draft document (docxcompose): appended resumes were re-styled by the
proposal's own style definitions ("Heading 1" etc. collide by name and the
master wins), page boundaries drifted, and PDF-only resumes couldn't be
included at all. Inspecting the historical references settled the question:
every reference `.docx` (drafts and the FINAL) ends at the "Appendix" heading
— the resume pages exist only in the deliverable PDF, and each page is the
person's own PDF export (their individual footers are visible in the
reference PDF).

## Decision

The `.docx` never contains resumes. Build produces two artifacts:

1. The draft `.docx` (working copy; ends at the Appendix heading).
2. `<draft> (SUBMITTAL).pdf` — the body exported via Word (`docx2pdf`,
   COM-initialized per worker thread) followed by each matched person's
   one-page resume PDF, merged with `pypdf` in Section II order. One-page
   `.docx` resumes are converted through Word at build time; resume picking
   prefers the newest one-page `.pdf` per person.

Compliance size/page checks measure the assembled PDF (the actual attachment).

## Alternatives Considered

| Alternative | Benefits | Drawbacks |
| --- | --- | --- |
| docxcompose merge into the .docx | single artifact | style collisions restyle resumes; PDFs excluded; diverges from how the real submittals are built |
| Manual assembly by the user | zero code | error-prone yearly ritual; ordering/selection mistakes; the automation's whole point |
| Rasterize resumes to images in the .docx | style-proof | heavy deps, quality loss, not editable, still not the real workflow |

## Rationale

PDF-level assembly reproduces the verified historical workflow exactly and is
formatting-proof: pages are the source PDFs themselves, so nothing is
re-rendered. First implementation was verified page-for-page against the
FY2026 reference PDF (equal page count; identical resume pages, people, and
order; matching file footprint).

## Consequences

- ProPosal now requires Windows + Word (`docx2pdf`) to assemble; without Word
  it falls back to a user-exported companion PDF or flags the step.
- `docxcompose` dependency removed.
- Resume quality control shifts to the folder: the newest one-page PDF per
  person is what ships, so keeping those exports current is the maintenance
  task (the cross-reference panel and flags surface staleness).
- The draft `.docx` remains the working copy / next cycle's input; the PDF is
  disposable output.

## Follow-Up

- Consider a picker preference knob if the naming convention changes (the
  "one-page" heuristic is intentionally simple and isolated in
  `resumes._pick_resume`).

## Evidence

- `ProPosal/proposal/jobs.py` (`_assemble_submittal`), `pdfutil.py`
  (`merge_pdfs`, `export_pdf`), `resumes.py` (`_pick_resume`).
- Reference PDFs under `ProPosal/assets/refs/` (git-ignored business docs):
  drafts' docx appendices empty; deliverable PDF = body + per-person pages.
- ProPosal CHANGELOG 0.12.0; session handoff 2026-07-02-2245 (round 8).
