# Project Context And Memory

The `docs/` directory is the repository's shared context and memory layer for
humans, coding AI, and other automation. It is tool-neutral: no vendor, model,
chat history, hidden workspace, or private memory is authoritative.

Start with [`context-contract.md`](context-contract.md), then use this index to
load only the context needed for the current task.

## Memory Model

| Memory type | Location | Purpose |
| --- | --- | --- |
| Current context | `context/` | Living project state, architecture, constraints, and active concerns |
| Reference | `reference/` | Stable contracts, inventories, schemas, terminology, and external references |
| Decisions | `decisions/` | Accepted choices, rationale, alternatives, and consequences |
| Plans | `plans/` | Proposed or active implementation sequences |
| Sessions | `sessions/` | Chronological handoffs describing work performed and remaining |
| Audits | `audits/` | Point-in-time reviews, findings, evidence, and recommendations |
| Runbooks | `runbooks/` | Repeatable setup, deployment, recovery, and operational procedures |
| Highlights | `highlights/` | Public, sanitized career artifacts: engineering case studies, resume bullets, and a skills matrix |

The first seven rows are internal memory. `highlights/` is a derived,
outward-facing layer curated from that memory for recruiters and interviewers;
it is public and sanitized, unlike the private `sessions/` and `audits/` notes.

This maps to four practical forms of memory:

- Semantic memory: `context/`, `reference/`, and `decisions/`.
- Episodic memory: `sessions/` and `audits/`.
- Prospective memory: `plans/`.
- Procedural memory: `runbooks/`.

## Read Order

At the start of a substantive task:

1. Read `docs/context-contract.md`.
2. Read `docs/context/current-state.md`.
3. Read the newest relevant file in `docs/sessions/`.
4. Read task-specific plans, decisions, audits, references, and runbooks.
5. Inspect the actual code, configuration, tests, and working tree before
   making claims or edits.

Do not load every document by default. Follow links and read only what is
needed to understand the task and avoid repeating prior work.

## Write Rules

- Put durable project knowledge in `docs/`, not only in chat or private tool
  memory.
- Work directly in the existing repository checkout. Do not create another
  workspace, worktree, clone, shadow copy, or parallel source tree inside or
  beside the codebase unless the user explicitly requests it.
- Use exact dates, file paths, commands, and verification results.
- Separate confirmed facts from assumptions, proposals, and unresolved
  questions.
- Link to an existing source instead of copying large blocks between files.
- Update living documents in place when the current truth changes.
- Never overwrite or silently rewrite dated historical records. Add a new
  dated document and cross-link it.
- Do not store secrets, credentials, access tokens, private user data, raw
  production payloads, or unnecessary full logs.
- Keep documents factual and concise enough for a new contributor to resume
  work without reading the original conversation.

## Workspace Integrity

The existing repository directory is the only working copy for a task.

- Do not create tool-managed workspaces or hidden alternate checkouts.
- Do not create Git worktrees, nested clones, copied project directories, or
  parallel source trees for delegation or experimentation.
- Do not redirect edits to a temporary copy of the repository.
- Temporary files that do not reproduce the project may use the operating
  system's temporary directory and must not become a competing source of truth.
- Other contributors or subprocesses must operate on the same checkout and
  preserve unrelated changes.
- If isolation is genuinely required, stop and obtain explicit user approval
  before creating any additional workspace.

## Naming

Living documents use stable names:

```text
docs/context/current-state.md
docs/reference/environment.md
docs/runbooks/deployment.md
```

Historical documents use dates:

```text
docs/sessions/YYYY-MM-DD-HHMM-short-title.md
docs/plans/YYYY-MM-DD-NN-short-title.md
docs/decisions/YYYY-MM-DD-NN-short-title.md
docs/audits/YYYY-MM-DD-NN-short-title.md
```

Use the local repository time zone. `NN` is a two-digit sequence used when
more than one document of the same type is created on a date.

Files beginning with `_`, such as `_TEMPLATE.md`, are exempt from date
prefixes.

## Source Precedence

When sources disagree, use this order and record meaningful conflicts:

1. Current user instructions and repository policy.
2. Executable reality: code, migrations, configuration, tests, and verified
   runtime behavior.
3. Accepted decision records.
4. Living context and reference documents.
5. Active plans.
6. Historical sessions and audits.

Plans describe intent, not completed work. Session notes and audits describe a
point in time and may become stale.

## Definition Of Done

A substantive task is complete when:

1. The requested outcome is implemented or the blocker is explicit.
2. Relevant verification is recorded as pass, fail, or not run with a reason.
3. Durable decisions, findings, procedures, or changed context are saved in
   the correct `docs/` location.
4. A session handoff records the final state and remaining work.

Purely conversational questions and trivial read-only lookups do not require a
session handoff.
