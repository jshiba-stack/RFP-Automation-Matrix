# Decision: ProPosal supports two build modes — refresh-from-FINAL and generate-from-data

> Date: 2026-06-30
> Status: accepted
> Supersedes: none
> Superseded by: none

## Context

The annual submittal is a formatting-heavy Office document. Most years it changes
only in a few variable fields; occasionally it needs rebuilding from scratch.
Neither a pure "regenerate everything" nor a pure "hand-edit last year's" approach
serves both cases well.

## Decision

ProPosal offers two modes, both formatting-preserving:
1. **Refresh from last year's FINAL `.docx`** — auto-update the variable fields
   (fiscal year, dates, ongoing-project end dates) and flag the rest for review.
2. **Generate from a data store** — rebuild the Capacity and Qualifications tables
   from structured data.
Every draft runs a compliance checklist + format check regardless of mode.

## Alternatives Considered

| Alternative | Benefits | Drawbacks |
| --- | --- | --- |
| Regenerate-only | Clean, data-driven | Loses accumulated manual formatting; risky for a document that's mostly stable |
| Hand-edit-only | Preserves formatting | Error-prone yearly diffs; no rebuild path |
| Both modes + compliance/format check (chosen) | Fits both the stable-year and the rebuild case; formatting preserved either way | More surface to maintain |

## Rationale

The stable-year path (refresh + flag) is low-risk and fast; the generate path
covers rebuilds. A shared compliance/format check keeps every output valid.

## Consequences

- Positive: right tool for both the incremental year and the rebuild.
- Cost: two code paths plus the checker to maintain.

## Follow-Up

- PDF form-fill: DPW-120 supported; SF330 pending a fillable template.

## Evidence

- `ProPosal/README.md`, `ProPosal/CHANGELOG.md` v0.7.0; root `CHANGELOG.md`
  2026-06-30.
