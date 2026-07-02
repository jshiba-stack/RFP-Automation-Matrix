# Repository Context Contract

Use this document as both the prompt and the operating contract for any human,
coding AI, or automation contributing to this repository.

## Canonical Prompt

```md
Treat this repository's `docs/` directory as shared, durable project memory.
The contract is tool-neutral. Do not rely on chat history, hidden files,
vendor-specific memory, or an individual contributor's private notes as the
source of truth.

Before substantive work:

1. Read `docs/README.md`.
2. Read `docs/context/current-state.md`.
3. Read the newest relevant handoff in `docs/sessions/`.
4. Read any task-specific decision, plan, audit, reference, or runbook.
5. Inspect the actual code, configuration, tests, and working tree.

While working:

- Prefer verified repository evidence over stale documentation.
- Work only in the existing repository checkout. Do not create a separate
  workspace, worktree, clone, copied project, shadow tree, or hidden
  tool-managed checkout unless the user explicitly requests it.
- Preserve unrelated work and keep changes scoped to the request.
- Record assumptions and distinguish them from confirmed facts.
- Save durable knowledge in the appropriate `docs/` category.
- Never store secrets, credentials, private data, or unnecessary raw logs.
- Update a living document when current truth changes.
- Create a new dated document for historical work; do not rewrite history.
- Do not claim a result was verified unless the command or check ran.

At the end of substantive work:

1. Run the relevant verification.
2. Update current context if project state changed materially.
3. Save any decision, plan, audit finding, reference, or procedure that should
   survive the conversation.
4. Create `docs/sessions/YYYY-MM-DD-HHMM-short-title.md` from the session
   template.
5. Record open work, blockers, uncommitted changes, and things already ruled
   out so the next contributor does not repeat them.

Follow `docs/README.md` for naming, source precedence, and the definition of
done.
```

## Category Contract

### Context

Use `docs/context/` for living documents that answer: "What is true now?"

Update these files in place. Include a last-reviewed date and links to evidence
or decisions. Do not use context files as chronological work logs.

### Reference

Use `docs/reference/` for stable facts and interfaces: terminology, environment
variables, service inventories, API contracts, data ownership, and external
source links.

Reference documents should describe, not decide. Put rationale in a decision
record and procedures in a runbook.

### Decisions

Use `docs/decisions/` when a choice affects architecture, product behavior,
security, operations, compatibility, or future work.

Decision records are append-only history. If a decision changes, create a new
record that supersedes the old one and link both directions.

### Plans

Use `docs/plans/` for non-trivial future work. A plan must state scope,
assumptions, ordered steps, risks, likely files, and verification.

Update a plan's status while it is active. When implementation materially
departs from it, record why. A plan is never evidence that work is complete.

### Sessions

Use `docs/sessions/` for concise chronological handoffs after substantive work.
A substantive task changes code, configuration, documentation, infrastructure,
or produces analysis that future contributors should retain.

Session notes capture evidence and state, not a transcript or a model's chain
of thought. Record `## User Prompt(s)` by default and quote the actual user
prompt when practical. Paraphrase or redact only when privacy, security, legal,
or confidentiality concerns make verbatim inclusion inappropriate.

### Audits

Use `docs/audits/` for point-in-time code, security, product, dependency,
performance, accessibility, or live-system reviews.

Separate confirmed findings from hypotheses. Rank findings, include evidence
and reproduction steps, and record non-issues that prevent duplicate work.

### Runbooks

Use `docs/runbooks/` for repeatable procedures. A runbook must include
prerequisites, safety checks, commands or actions, expected results,
verification, rollback or recovery, and escalation conditions.

Do not put one-time investigative history in a runbook.

## Maintenance Contract

- `docs/README.md` is the canonical router.
- `docs/context/current-state.md` is the concise active-state summary.
- Root compatibility files may point into `docs/`, but must not duplicate or
  override this contract.
- The current repository checkout is the sole working copy. Any additional
  workspace requires explicit user approval before creation.
- Links should be repository-relative and remain valid after cloning.
- Obsolete living content should be corrected or explicitly marked obsolete.
- Historical documents should remain available unless retention, privacy, or
  security policy requires removal.
- When a document is contradicted by verified implementation, fix the living
  document and mention the discrepancy in the session handoff.

## Reusable Task Prompt

```md
Follow the repository context contract in `docs/context-contract.md`.

Task:
[Describe the requested outcome.]

Constraints:
- Work directly in the existing checkout. Do not create a separate workspace,
  worktree, clone, or copied project.
- Preserve unrelated changes.
- Keep implementation and documentation scoped to the task.
- Verify relevant behavior and report exact results.
- Save durable context in the correct `docs/` category.
- Finish with a session handoff for substantive work.
- Do not commit, push, deploy, or mutate live infrastructure unless explicitly
  requested.
```
