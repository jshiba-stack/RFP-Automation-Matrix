# Highlights (Career Layer)

This folder is the **public, sanitized, hiring-manager-facing** view of the work
in this repository. It is the mirror image of `docs/sessions/`: session notes are
private, internal, and written for the next contributor; highlights are public,
curated, and written for a recruiter or an interviewer.

Nothing here contains real client, firm, personnel, or contact data. Every
artifact uses the same fictional or generic framing as the committed tests, and
describes the engineering rather than the real people involved. See the
[public-repo privacy posture](../decisions/2026-06-30-01-public-repo-privacy-posture.md).

## What lives here

| File | Audience | Purpose |
| --- | --- | --- |
| [case-studies.md](case-studies.md) | Technical interviewer (minutes) | The best problems solved, written STAR-style (Situation, Task, Action, Result). Interview stories and the source of the resume bullets. |
| [resume-bullets.md](resume-bullets.md) | Recruiter / ATS skim (seconds) | The same wins compressed to one line each, with metrics, ready to paste into a resume or LinkedIn. |
| [skills-matrix.md](skills-matrix.md) | Both | Competencies mapped to concrete evidence, so a skim instantly connects this work to a job description. |

## How this work was built (honest framing)

These projects were built with AI-assisted development: a model produced much of
the implementation under direction. The engineering owned by the author is the
part that matters for hiring, and it is real: identifying the problem, choosing
the architecture, making and defending the tradeoffs, evaluating the output and
rejecting wrong paths, and verifying the result. That is the same place a lead or
staff engineer already spends their value, and it is where the case studies are
written from.

This framing is deliberate and honest. Tune or remove this section to fit how you
want to present your method.

## The integrity rule

Claim only what you can explain unaided. Every case study is a promise that the
author can walk any engineer through it from memory, with no notes. If a claim
cannot pass that test, it is learned cold before it is claimed, or it is not
claimed.

## Metric honesty

Two tiers, always kept distinct:

- **Measured** metrics are checkable facts (test counts, file sizes, verified
  page counts). Use freely.
- **Estimated** metrics (time saved, manual baseline) are labeled `(est.)` and
  backed by a stated basis the author can defend.

Product-efficiency metrics (does the built system run cheaply, offline, or fast)
belong here. Construction-cost metrics (how much compute it took to build) do
not.

## Harvesting (how to keep this current)

This layer is not produced by the `/documentation` skill. It is curated:

1. After notable work, the raw material lands in `docs/sessions/` (private) and
   the changelogs (public) as usual.
2. Periodically, promote the best problems into a case study here: rewrite in the
   STAR + author-owned voice, sanitize all real data, and mark metrics
   measured or estimated.
3. Regenerate the resume bullets and skills matrix from the case studies.

The promotion step is a judgment call (which problems are the strongest, how to
sanitize them), which is why it stays manual.
