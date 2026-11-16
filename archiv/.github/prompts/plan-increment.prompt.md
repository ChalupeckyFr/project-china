---
name: plan-increment
description: 'Turn an approved scope into solution decisions and small, verifiable tasks. Compares options, records DEC-*, creates T-* in TASKS.md. Does not install or implement.'
argument-hint: 'Approving DEC-* id (e.g. DEC-001), or "aktuální" for the scope referenced in PROJECT.md.'
agent: agent
---

# Plan increment

## Language

Talk to the human in Czech. Write documents in the language set in
`AGENTS.md`. Keep IDs and state slugs ASCII.

## Load first (actually open these files)

1. `AGENTS.md` – sections 3 (lifecycle), 4 (autonomy, approvals), 5 (records), 8 (verification).
2. `PROJECT.md` – phase, active increment, blocking `Q-*`.
3. `DECISIONS.md` – the scope-approval `DEC-*` and any delegation `DEC-*`.
4. `SPEC.md` – only the `FR/NFR/CON/AC` records listed in that approval.

## Preconditions (check, do not assume)

- A `DEC-*` of type `schvaleni-rozsahu` with a filled `Schválení` block exists
  and the referenced records are `schvaleno`.
- No `Q-*` with `Blokuje` pointing at those records is `otevreno`.

If a precondition fails: list the concrete missing items as questions and
stop with a pointer back to `/discover-project`. Do not plan around gaps.

## Part A – Solution design (phase `navrh-reseni`)

1. Identify technical decisions the increment needs (architecture, stack,
   data storage, integrations, toolchain). Respect every `CON-*`.
2. For each: compare only meaningful options (2–3), state trade-offs, risks,
   and a recommendation. Record as `DEC-*` state `navrh`.
3. Decisions covered by an existing delegation `DEC-*` may be set to
   `prijato` with a reference to that delegation. All others → state
   `ke-schvaleni`, present them to the human, **STOP and wait**.
4. Never set `prijato` yourself for decisions touching cost, external data
   transfer, security boundaries or scope.

## Part B – Task breakdown (phase `planovani-prirustku`)

Only after required decisions are `prijato`:

1. Create `T-*` records in `TASKS.md` using its "Vzor" format. Keep each
   task small (one reviewable change), with `Vazby` to `AC-*` or `DEC-*`,
   explicit `Závislosti`, and a realistic `Ověření → Plán`.
2. Ensure every `AC-*` of the increment is covered by at least one task.
   Report any gap instead of inventing an AC.
3. If the project has no toolchain yet, include tasks for: toolchain setup,
   first checks (lint/test skeleton), and one thin end-to-end slice. Do not
   plan the whole product.
4. Set tasks whose dependencies, approvals and verification are ready to
   `pripraveno`; others stay `nezahajeno`.
5. Update `PROJECT.md`: phase `realizace`-ready status is **not** set here;
   record the active increment, and "Další krok" = first ready task ID.

## Not allowed

- Installing, running, implementing, or committing.
- Creating tasks without an approved scope or without `Vazby`.
- Modifying `SPEC.md` content – new findings go to `Q-*` or back to discovery.

## Handover output (in Czech)

- Decisions created, grouped by state (`prijato` / `ke-schvaleni`).
- Tasks created with their states and the dependency order.
- AC coverage table (AC → tasks) and gaps.
- First task to run: `/work-task T-xxx`.
