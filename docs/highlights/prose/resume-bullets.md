# Resume Bullet Bank: ProSE

One-line, paste-ready versions of the [ProSE case studies](case-studies.md). Each
is written to survive a seconds-long skim and to hold up when an interviewer asks
you to expand it. Metrics are marked `(measured)` or `(est.)`; keep those labels
in your head, not in the resume, and be ready to defend any estimate.

For suite-level bullets and summary lines, see the
[highlights index](../README.md). For the document-assembly program, see
[ProPosal bullets](../proposal/resume-bullets.md).

## Bullets

- Built a scheduled scanner that extracts matching procurement opportunities from
  public sources into a styled spreadsheet and emails it on a schedule, replacing
  roughly 2 hours of manual portal-checking and data entry per scan with an
  unattended job `(est.)`.
- Architected the extractor to run with zero LLM inference: the same per-scan
  extraction done by prompting a model would process roughly 70,000 tokens per
  scan (about 480,000 per week at a daily cadence); the deterministic pipeline
  handles it with no model call, offline and private `(est.; basis below)`.
- Made an automated refresh run safely alongside a human collaborator on one
  shared workbook: non-destructive column updates, dedup by stable key, and
  preservation of the user's own formatting on every run `(measured)`.
- Root-caused recurring duplicate records to a pipeline ordering defect, where a
  later enrichment step overwrote the very identifier the de-duplication had
  grouped on, and shipped a self-healing merge that collapsed the existing
  duplicates while preserving human-entered values from both copies `(measured)`.
- Found and fixed a latent second instance of the same bug class in the same
  code path (search-result markup leaking into the record key) before it ever
  produced a defect `(measured)`.
- Rebuilt a concurrency guard after testing its premise and finding it false for
  cloud-synced files, which take no exclusive OS lock when co-authored, then
  added a crash-recovery failsafe gated on a liveness probe so it can never
  disarm the guard it protects `(measured)`.
- Reverse-engineered an undocumented public search API's matching semantics
  through systematic probing, and redesigned the keyword strategy on that
  evidence rather than on assumption `(measured)`.
- Added lock-aware concurrency (skip-and-retry on a locked file) and an opt-in
  column lock on the dedup key, eliminating lost scans and duplicate rows on a
  synced shared drive `(measured)`.
- Implemented resilient scheduling via the OS task scheduler so jobs run without
  the app open and survive reboots, with a one-command kill switch `(measured)`.

## Basis for the estimated metrics

Keep these so you can defend any estimate in an interview. Update the anchors as
you refine them.

- **Scan time saved:** manual keyword-checking across both portals plus recording
  about 2 hours per scan (your figure); the scheduled job runs unattended.
- **Token throughput avoided:** models the hypothetical of doing each scan by
  prompting a model. Assumes about 30 solicitations per scan, about 2,000 input
  and 300 output tokens each (about 69,000 tokens per scan), run daily (about
  480,000 tokens per week, about 25M per year). The product itself uses no model,
  so this is processing the deterministic design handles with zero inference, not
  cost that was ever paid. Report it in tokens, not dollars: the dollar cost of a
  single scan is negligible and model pricing shifts, whereas token throughput is
  a stable, model-agnostic figure.
- Lead with time saved and the zero-inference architecture (runs offline, free,
  private); those are the durable points.

## How to use this file

1. Choose the bullets that match the target role.
2. Replace `(measured)` and `(est.)` labels with the plain number in the resume
   itself.
3. Confirm you can expand each chosen bullet into the full
   [case study](case-studies.md) from memory before you submit.
