# Engineering Case Studies: ProPosal (Professional Services Proposal Builder)

Curated, sanitized narratives of the hardest problems solved in **ProPosal**, the
builder that assembles the annual professional-services submittal end to end.
Written STAR-style (Situation, Task, Action, Result) in the author-owned voice
described in the [highlights README](../README.md). Metrics are marked
`(measured)` or `(est.)`. No real client, firm, or personnel data appears here.

For the extraction program, see [ProSE case studies](../prose/case-studies.md).

---

## 1. Reverse-engineering a deliverable's real format with a verification loop

**Situation.** The submittal's Appendix must carry one resume page per team
member. The first build appended each person's resume from a Word file into the
proposal document, and the output's formatting came out completely wrong: it did
not resemble the real deliverable the firm actually ships.

**Task.** Determine what the finished deliverable genuinely is, then make the
build reproduce it exactly instead of guessing at styling fixes.

**Action.** Rather than keep tuning the merge styling, I ran a verification loop
against a ground-truth reference: I compared our output page-for-page against the
firm's historical deliverables, drafts and final, and re-ran that comparison after
every change. The comparison exposed the real cause. Every reference Word file
ends at the "Appendix" heading, which meant the resume pages never lived in the
Word document at all: they exist only in the delivered PDF, each one the person's
own PDF export (their individual page footers were visible in the reference).
Appending Word files was therefore the wrong mechanism outright, and it was
actively harmful, because the proposal's own styles collided by name and the
master document re-styled every resume. I re-architected assembly to the PDF
level: export the body through Word, then merge each person's one-page resume PDF
in section order with a PDF library, with no re-rendering of anyone's page. I kept
running the same page-for-page loop until the assembled output matched the
reference exactly, which is also what let me retire the Word-merge dependency with
confidence.

**Result.** The assembled deliverable converged to match the reference
page-for-page. Because the pages are the source PDFs themselves, nothing is
re-rendered and the format is reproduced rather than approximated. The discovery
reversed the assembly architecture and let an entire dependency be removed.

- Output converged to the reference deliverable page-for-page: equal page count (21 of 21), identical resume pages, people, and order `(measured)`
- Root cause found by inspection, not assumption: reference Word files end at the Appendix heading, so resumes are PDF-only `(measured)`
- Word-merge dependency (`docxcompose`) removed once the loop confirmed the new path `(measured)`

**Demonstrates:** verifying against ground truth, iterative convergence loops,
rejecting a wrong architecture early, PDF and document pipeline engineering.

**Evidence:** [decision record](../../decisions/2026-07-04-01-pdf-level-submittal-assembly.md),
`ProPosal/proposal/jobs.py` (`_assemble_submittal`), `ProPosal/proposal/pdfutil.py`,
`ProPosal/proposal/resumes.py`.

---

## 2. Root-causing "stretched" text in an assembled PDF deliverable

**Situation.** The proposal builder assembles a final PDF from a Word-exported
body plus each team member's one-page resume PDF. Some pages rendered with text
that looked vertically elongated, and the obvious suspect was the PDF-merge step
distorting them.

**Task.** Find the true cause and make the build produce a consistent
deliverable no matter how poorly formed the source files are.

**Action.** I refused to accept the assumed cause and ran a measurement-first
diagnosis. Every page of the merged output was exactly Letter size and the
concatenation applied no scaling, which cleared the merge step of blame.
Inspecting the source PDFs' text layers, I traced the distortion to several files
that had been re-saved in a desktop PDF editor after their Word export: the
re-save rewrote the glyphs at unequal horizontal and vertical scale (up to 1.33
times taller than wide) and left fonts un-embedded. Because a PDF is final-form
and cannot be un-stretched in place, I designed a three-part response and owned
the key calls: a typography linter (flagging editor re-saves, non-uniform text
scale, and non-embedded fonts), a picker that prefers a clean same-generation
source over a mangled newer one, and a rebuild pipeline that re-typesets a resume
onto a house template when no clean source exists, gated by a lost-words check so
it never ships silently. I also ruled that content freshness must outrank
typography, after an earlier clean-first ordering was tried and rejected for
reaching back to stale files.

**Result.** Malformed pages now self-heal or are flagged for review, and the
deliverable carries one typographic standard. The linter immediately surfaced
additional non-uniform files no one had noticed.

- Text stretch detected via per-run scale matrices at a 5% deviation threshold `(measured)`
- Rebuilt pages re-typeset onto a house template, gated by a lost-words check so nothing ships silently `(measured)`
- Shipped with a test suite on fictional data in a public repository `(measured)`

**Demonstrates:** measure-before-fixing discipline, low-level PDF and document
engineering, designing for graceful degradation, test coverage on a public repo.

**Evidence:** [decision record](../../decisions/2026-07-08-01-resume-and-letterhead-standardization.md),
`ProPosal/proposal/pdfutil.py`, `ProPosal/proposal/resume_rebuild.py`.

---

## 3. Standardizing a document header across a multi-source deliverable

**Situation.** The firm header block (name, address, website) drifted across the
assembled document: several font sizes, multiple address spellings, five
horizontal positions, and one color in the body versus another on the resume
pages. The deliverable looked assembled from many places, because it was.

**Task.** Make the whole deliverable carry one identical header without editing
each source file by hand, and without hardcoding any real firm data into a public
repository.

**Action.** I decided the body document is the single source of truth for the
standard, and that the standard should be measured from it at build time rather
than hardcoded. The proofread pass normalizes every header-looking line in the
draft to one size and color, right-aligned to the content margin, while excluding
the paragraph that holds the logo so alignment never drags the artwork with it.
At assembly, the body's header block is measured and re-set through Word as a
position-calibrated stamp, then merged over each resume page's own header after
whiting it out, shifted vertically by that page's measured logo offset so the
block sits relative to the logo exactly as the body's does. A safety check leaves
any header zone that contains non-standard text untouched and flags it instead of
guessing.

**Result.** Every page now shows one identical header in position, size, and
color. All firm-specific values come from configuration and measured content, so
the committed code carries no real data.

- Header size, color, and right-edge position verified uniform across all pages of a real build `(measured)`
- No firm data in committed source; header detection is pattern-matched `(measured)`

**Demonstrates:** treating a document as a programmable artifact, calibration
against real output, public-repo hygiene, defensive fallbacks.

**Evidence:** [decision record](../../decisions/2026-07-08-01-resume-and-letterhead-standardization.md),
`ProPosal/proposal/proofread.py`, `ProPosal/proposal/pdfutil.py`.

---

## 4. A cost- and privacy-conscious classifier with a deterministic fallback

**Situation.** One section of the submittal lists professional-service categories
that must be reconciled against a government agency's annually-published lettered
taxonomy. Doing this by hand is slow and error-prone, and the source categories
rarely match the taxonomy names exactly.

**Task.** Automate the reconciliation without making the tool depend on a paid
API, leak private content to a third party, or break when no model is available.

**Action.** I built a parser that reads the agency's lettered list from the
annual notice, and a classifier that auto-applies exact-name matches and flags
everything uncertain or duplicated for review. For the fuzzy remainder I made a
deliberate architecture choice: the AI layer is optional and off by default. A
local model backend sharpens the suggestions when it is present, and a
deterministic matcher handles the common cases with no model call at all. The
default path is therefore free, offline, and private, with the model as an
opt-in enhancement rather than a hard dependency.

**Result.** Common cases are classified with no model call, the tool runs with
nothing extra installed, and private content never leaves the machine unless the
user deliberately turns the local model on. At build time the section is rebuilt
to a house standard automatically (letters reconciled and normalized, duplicates
combined, canonical names applied).

- Default classification path requires no external API and no network call `(measured)`
- Exact-name matches auto-applied; uncertain and duplicate entries flagged for human review `(measured)`

**Demonstrates:** pragmatic AI integration, designing for graceful degradation,
privacy-by-default architecture, knowing when not to call a model.

**Evidence:** `ProPosal/proposal/skills.py`, `ProPosal/proposal/dit_taxonomy.py`,
`ProPosal/proposal/llm/`.
