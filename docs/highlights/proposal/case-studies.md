# Engineering Case Studies: ProPosal (Professional Services Proposal Builder)

Curated, sanitized narratives of the hardest problems solved in **ProPosal**, the
builder that assembles the annual professional-services submittal end to end.
Written STAR-style (Situation, Task, Action, Result) in the author-owned voice
described in the [highlights README](../README.md). Metrics are marked
`(measured)` or `(est.)`. No real client, firm, or personnel data appears here.

For the extraction program, see [ProSE case studies](../prose/case-studies.md).

---

## 1. Root-causing "stretched" text in an assembled PDF deliverable

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
- Assembled output verified page-for-page identical to a prior reference, 21 of 21 pages `(measured)`
- Shipped with a test suite on fictional data in a public repository `(measured)`

**Demonstrates:** measure-before-fixing discipline, low-level PDF and document
engineering, designing for graceful degradation, test coverage on a public repo.

**Evidence:** [decision record](../../decisions/2026-07-08-01-resume-and-letterhead-standardization.md),
`ProPosal/proposal/pdfutil.py`, `ProPosal/proposal/resume_rebuild.py`.

---

## 2. Standardizing a document header across a multi-source deliverable

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

## 3. A cost- and privacy-conscious classifier with a deterministic fallback

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
