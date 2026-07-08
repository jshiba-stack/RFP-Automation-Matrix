# Decision: Standardize resume pages by rebuild-and-restamp, never in-place repair

> Date: 2026-07-08
> Status: accepted
> Supersedes: none
> Superseded by: none

## Context

Some resume source PDFs render with visibly broken typography (text drawn up
to 33% taller than designed, substituted fonts): they were re-saved by a
desktop PDF editor after their Word export, which re-writes the text layer.
A PDF is final-form — glyph scaling cannot be "un-stretched" in place. The
letterhead block (firm name + address + site, top right) had also drifted
across the deliverable: two font sizes, three address spellings, five
positions, and a blue firm name in the body vs black on resumes.

## Decision

1. **Detect, prefer, rebuild — in that order.** Every resume PDF merged into
   the submittal is linted (editor re-save, non-uniform text scale,
   non-embedded fonts, off-Letter page). The picker prefers a clean
   *same-generation* sibling over an editor-mangled newest copy — but content
   freshness always beats typography (an older clean copy never wins). Only
   when no clean source exists is the page **re-typeset onto the house
   template** (`proposal/resume_rebuild.py`), gated by a lost-words check and
   never silent: REVIEW flag + "(REBUILT)" footer tag.
2. **The submittal body is the letterhead anchor.** The standard is measured
   from the body at build time (not hardcoded): black, 9pt (contact blocks
   conventionally sit below body size), right edge flush with the content
   margin, vertical position fixed relative to the logo. The body PDF's block
   is re-set via Word as a calibrated stamp and merged over every resume
   page's own block (whiteout + overlay, per-page logo-offset shift), so the
   deliverable carries one identical letterhead. A header zone containing
   non-letterhead text is left untouched and flagged.
3. **House standard rules live in code as single knobs** —
   `proofread.LETTERHEAD_FONT_PT`, the firm-neutral letterhead pattern, the
   "current employer ends in Present" rule — with no firm data in committed
   code (public repo).

## Consequences

- A damaged source PDF can no longer ship distorted or inconsistent pages;
  every deviation is either healed automatically or flagged for a human.
- The old header text remains beneath the whiteout in the PDF text layer
  (visual standard only) — harmless, but text extraction sees both blocks.
- Rebuilds depend on Word (already a hard requirement) and are cached under
  the git-ignored output dir; promoting a rebuild to a person's real resume
  is a deliberate manual copy, so builds never mutate the shared OneDrive.
