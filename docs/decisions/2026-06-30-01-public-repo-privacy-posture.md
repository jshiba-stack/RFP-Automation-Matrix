# Decision: Public repo, but all business data stays out; examples are fictional

> Date: 2026-06-30
> Status: accepted
> Supersedes: none
> Superseded by: none

## Context

The repo is public (MIT). The tool operates on real procurement documents,
firm/personnel details, client contacts, and generated exports — none of which
should ever be public.

## Decision

Keep the code public but hard-exclude all business content: a hardened root
`.gitignore` keeps proposals, forms, notices, exports, and firm/reference/contact
data out of the repo. The bundled example data store and tests use **fictional
placeholder data only**. (The docs/ memory framework extends this: `docs/sessions/`
and `docs/audits/` are git-ignored working notes.)

## Alternatives Considered

| Alternative | Benefits | Drawbacks |
| --- | --- | --- |
| Make the repo private | Simplest way to protect data | Loses the public/portfolio value of the code |
| Public + strict gitignore + fictional examples (chosen) | Code is shareable; real data never leaves the machine | Requires discipline; a mistaken commit is public and permanent |

## Rationale

The code is worth showing; the data is not. Excluding business content at the
`.gitignore` layer and shipping only fictional examples lets the project be
public safely.

## Consequences

- Positive: shareable/portfolio-visible code with zero real data exposed.
- Cost: every contributor/tool must respect the exclusions; anything committed to
  a public repo is permanent, so verify before pushing.

## Follow-Up

- Before each push, confirm no business documents or real data are staged.

## Evidence

- Root `CHANGELOG.md` 2026-06-30 ("Hardened the root `.gitignore` …");
  root `.gitignore`; verified: no tracked business binaries in the repo.
