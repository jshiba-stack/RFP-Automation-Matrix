# Decision: Structure the project as a suite of self-contained programs

> Date: 2026-06-27
> Status: accepted
> Supersedes: none
> Superseded by: none

## Context

The procurement workflow has distinct stages (discover/track vs. build the
submittal). Building one monolith would couple unrelated concerns and make each
stage hard to run or version on its own.

## Decision

One folder per program, each self-contained: its own README, CHANGELOG, version,
`.venv`, and dependencies, independently runnable. The suite root holds only the
overview and suite-level milestones. Programs connect as a discover → pursue
pipeline but share no code. (Established with ProSE v0.1.0; ProPosal added as the
second program.)

## Alternatives Considered

| Alternative | Benefits | Drawbacks |
| --- | --- | --- |
| Single monolith | One codebase | Couples discovery and submittal-building; hard to run/version independently |
| Program suite (chosen) | Independent run/version; clear boundaries; add programs incrementally | Some duplication (per-program venv/deps) |

## Rationale

Independent programs can be run and released on their own cadence and reasoned
about separately, matching the sibling projects' convention.

## Consequences

- Positive: each stage is independently runnable and versioned.
- Cost: per-program environment duplication.

## Evidence

- Root `README.md` (Conventions, Repository layout); root `CHANGELOG.md`
  2026-06-27, 2026-06-30.
