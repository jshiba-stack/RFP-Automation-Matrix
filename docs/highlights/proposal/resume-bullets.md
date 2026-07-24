# Resume Bullet Bank: ProPosal

One-line, paste-ready versions of the [ProPosal case studies](case-studies.md).
Each is written to survive a seconds-long skim and to hold up when an interviewer
asks you to expand it. Metrics are marked `(measured)` or `(est.)`; keep those
labels in your head, not in the resume, and be ready to defend any estimate.

For suite-level bullets and summary lines, see the
[highlights index](../README.md). For the extraction program, see
[ProSE bullets](../prose/resume-bullets.md).

## Bullets

- Reduced the annual professional-services submittal from roughly 25 hours of
  manual assembly to a roughly 3-minute automated build (est., about a 99%
  reduction), producing the final multi-section PDF deliverable end-to-end.
- Root-caused a document-rendering defect by analyzing PDF glyph-scale matrices,
  disproving the assumed cause, and shipped a lint-and-rebuild pipeline that
  standardizes malformed source files automatically.
- Reverse-engineered a deliverable's true format by comparing output page-for-page
  against a ground-truth reference in a verification loop, discovering the resume
  pages were PDF-only and re-architecting assembly from Word-merge to PDF-level
  (an entire dependency removed) `(measured)`.
- Built a PDF assembly pipeline that merges a Word-exported body with per-person
  resume pages and converged the output to the reference, 21 of 21 pages identical
  `(measured)`.
- Designed a build-time proofread pass that enforces one document-wide standard
  for tables, pagination, and header blocks across files from many sources, with
  no firm data hardcoded into a public repo.
- Integrated an optional local LLM behind a deterministic fallback so the default
  classification path runs free, offline, and private, with the model as opt-in
  enhancement rather than a dependency.
- Cut the assembled deliverable from 3.47 MB to 2.26 MB by deduplicating
  identical objects across merged PDF parts, bringing it back under a hard size
  cap `(measured)`.
- Maintained a test suite of 100-plus cases on fictional data in a public
  repository `(measured)`.

## Basis for the estimated metrics

Keep these so you can defend any estimate in an interview. Update the anchors as
you refine them.

- **Submittal time saved:** manual assembly about 25 hours per submittal (your
  figure), automated build about 3 minutes. Reduction about 99%. Per submittal.

## How to use this file

1. Choose the bullets that match the target role.
2. Replace `(measured)` and `(est.)` labels with the plain number in the resume
   itself.
3. Confirm you can expand each chosen bullet into the full
   [case study](case-studies.md) from memory before you submit.
