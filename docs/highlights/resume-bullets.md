# Resume Bullet Bank: RFP Automation Matrix

One-line, paste-ready versions of the [case studies](case-studies.md). Each is
written to survive a seconds-long skim and to hold up when an interviewer asks you
to expand it. Metrics are marked `(measured)` or `(est.)`; keep those labels in
your head, not in the resume, and be ready to defend any estimate.

Pick the strongest three to five for any given application and tailor the verbs to
the job description.

## Summary-line options (top of resume)

- Software engineer who ships end-to-end automation for real stakeholder
  workflows, with a bias for root-cause diagnosis, test coverage, and verified
  outcomes.
- Builder who directs AI to produce production-quality tools and owns the
  engineering that matters: architecture, tradeoffs, evaluation, and
  verification.

## ProPosal (document assembly and standardization)

- Reduced the annual professional-services submittal from roughly 25 hours of
  manual assembly to a roughly 3-minute automated build (est., about a 99%
  reduction), producing the final multi-section PDF deliverable end-to-end.
- Root-caused a document-rendering defect by analyzing PDF glyph-scale matrices,
  disproving the assumed cause, and shipped a lint-and-rebuild pipeline that
  standardizes malformed source files automatically.
- Built a PDF assembly pipeline that merges a Word-exported body with per-person
  resume pages and verified the output page-for-page against a reference, 21 of 21
  pages identical `(measured)`.
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

## ProSE (scheduled extraction and safe shared data)

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
- Added lock-aware concurrency (skip-and-retry on a locked file) and an opt-in
  column lock on the dedup key, eliminating lost scans and duplicate rows on a
  synced shared drive `(measured)`.
- Implemented resilient scheduling via the OS task scheduler so jobs run without
  the app open and survive reboots, with a one-command kill switch `(measured)`.

## Suite-level (process and security)

- Ran a full git-history privacy audit, found and removed real data leaks with a
  history rewrite after a backup, verified zero remaining hits, and hardened the
  documentation process to make the privacy check mandatory `(measured)`.
- Established a tool-neutral documentation and memory framework (context,
  decisions, sessions, audits, runbooks) so any contributor can resume work
  without the original conversation.

## Basis for the estimated metrics

Keep these so you can defend any estimate in an interview. Update the anchors as
you refine them.

- **Submittal time saved:** manual assembly about 25 hours per submittal (your
  figure), automated build about 3 minutes. Reduction about 99%. Per submittal.
- **Scan time saved:** manual keyword-checking across both portals plus recording
  about 2 hours per scan (your figure); the scheduled job runs unattended.
- **Token throughput avoided (ProSE):** models the hypothetical of doing each scan
  by prompting a model. Assumes about 30 solicitations per scan, about 2,000 input
  and 300 output tokens each (about 69,000 tokens per scan), run daily (about
  480,000 tokens per week, about 25M per year). The product itself uses no model,
  so this is processing the deterministic design handles with zero inference, not
  cost that was ever paid. Report it in tokens, not dollars: the dollar cost of a
  single scan is negligible and model pricing shifts, whereas token throughput is
  a stable, model-agnostic figure.
- Lead with time saved and the zero-inference architecture (runs offline, free,
  private); those are the durable points. Express inference cost-avoidance in
  token throughput, not dollars.

## How to use this file

1. Choose the bullets that match the target role.
2. Replace `(measured)` and `(est.)` labels with the plain number in the resume
   itself.
3. Confirm you can expand each chosen bullet into the full
   [case study](case-studies.md) from memory before you submit.
