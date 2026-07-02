# Repository Context Entry Point

This file is a compatibility entry point for coding tools that automatically
look for `CLAUDE.md` or `AGENTS.md`. It is not the canonical project memory.

## Start Here

1. Read `docs/README.md`.
2. Follow `docs/context-contract.md`.
3. Read `docs/context/current-state.md`.
4. Read the newest relevant handoff in `docs/sessions/`.
5. Inspect the working tree before editing.

The complete project context, decisions, plans, audits, handoffs, references,
and procedures live under `docs/`.

## Repository Rules

- Work directly in this existing checkout. Do not create a separate workspace,
  worktree, clone, copied project directory, shadow source tree, or hidden
  tool-managed checkout unless the user explicitly requests it.
- Preserve unrelated work and keep changes scoped to the request.
- Update `docs/context/current-state.md` when current truth changes.
- Create a dated session handoff after substantive work.
- Do not commit, push, deploy, or mutate live infrastructure unless explicitly
  requested.
