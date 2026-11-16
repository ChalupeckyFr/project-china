---
name: work-task
description: 'Execute one prepared task T-*: verify readiness, make a small bounded change, run real checks, record evidence. Does not commit, publish or continue to the next task without permission.'
argument-hint: 'Task id, e.g. T-003. If omitted, the agent asks unless PROJECT.md names the next task.'
agent: agent
---

# Work task

## Language

Talk to the human in Czech. Write documents in the language set in
`AGENTS.md`. Keep IDs and state slugs ASCII.

## Load first (actually open these files)

1. `AGENTS.md` – sections 4.1 (autonomy table), 6 (session), 8 (verification).
2. `PROJECT.md` – phase, "Bod pokračování", blocking `Q-*`.
3. `TASKS.md` – the task record and its `Závislosti`.
4. Referenced `AC-*` in `SPEC.md` and `DEC-*` in `DECISIONS.md`.
5. Actual state of the files the task touches (worktree, not memory).

## Select the task

- Use the ID from the argument.
- No argument → use "Další krok" in `PROJECT.md` only if it names exactly
  one task; otherwise list `pripraveno` tasks and ask.

## Readiness check (all must hold, else stop and report)

- State is `pripraveno` (or `rozpracovano` when resuming).
- All `Závislosti` are `dokonceno`.
- Required approvals/permissions exist for every operation the task needs
  (see autonomy table). Installing, running services, committing, external
  transfers need explicit permission – check `DEC-*` or ask.
- `Ověření → Plán` is executable with the toolchain that actually exists.

Do not set a not-ready task to `rozpracovano`. Clarify first.

## Execute

1. Set state `rozpracovano`; note start in `PROJECT.md` "Bod pokračování".
2. Make the smallest change that satisfies "Hotovo když". Stay inside
   `Rozsah`. Do not touch unrelated files.
3. Run the planned checks for real. Use existing tools; never invent commands
   for a toolchain that does not exist; never report unrun checks as passed.
4. Max two attempts at the same failing approach, then stop and report.
5. Record evidence in `Ověření → Výsledek` per `AGENTS.md` section 8
   (what, revision, command, result, environment, skipped checks, deviations).
6. Set state: `k-overeni` if human acceptance is required by "Hotovo když",
   otherwise `dokonceno`. On block → `blokovano` with reason and unblock condition.
7. Update `PROJECT.md` "Bod pokračování". Do not copy task state there.

## Scope changes

A new requirement, a contradiction with `SPEC.md`, or a needed deviation is
**not** solved inside the task. Record it as `Q-*` (or `IDEA-*` if it is an
idea), keep the task within its original scope, and report it.
Never edit `SPEC.md` to match what was implemented.

## Not allowed without explicit permission

Commit, push, PR, publish, install dependencies, start services, delete
data, transfer project data externally, start the next task.

## Handover output (in Czech)

- Changes made (files, summary).
- Evidence: checks run and results; checks not run and why.
- Task state and reason.
- Blockers, deviations, new `Q-*`/`IDEA-*`.
- Whether human acceptance is needed and for what exactly.
- Proposed next task (ID) – ask before continuing.
