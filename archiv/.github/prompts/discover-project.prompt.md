---
name: discover-project
description: 'Start or resume product discovery: guided conversation about the need, users, scenarios, scope, data and constraints. Writes requirements into SPEC.md. Does not choose a stack or implement anything.'
argument-hint: 'Optional: what you already know about the product, or "pokračuj" to resume.'
agent: agent
---

# Discover project

## Language

Talk to the human in Czech. Write documents in the language set in
`AGENTS.md`. Keep IDs and state slugs ASCII.

## Load first (actually open these files)

1. `AGENTS.md` – especially sections 3.1 (vedení discovery), 4 (schvalování),
   5 (evidence).
2. `PROJECT.md` – phase, open questions `Q-*`.
3. `SPEC.md` – existing records and "Předpoklady".

If the phase is `pripraveno-ke-specifikaci`, set it to `discovery` now
(this prompt is the explicit human start). If `PROJECT.md` or `SPEC.md`
is missing, stop and ask the human to run bootstrap first.

## Allowed work

- Conversation following `AGENTS.md` 3.1: one important question at a time,
  need before technology, periodic summaries of understanding.
- Writing **only information the human actually gave** into `SPEC.md` as
  `FR-*`, `NFR-*`, `CON-*`, `AC-*` with state `navrh`, plus `Q-*` into
  `PROJECT.md`.
- Offering options with consequences and a recommendation when the human
  says "nevím" or "doporuč". Label the recommendation as agent proposal.
- Proposing bounded research as a `Q-*` or a future task – not running it.

## Not allowed

- Choosing a stack, framework, database, or architecture (that is
  `plan-increment` after approval). A stack **prescribed by the human** is a
  `CON-*`.
- Creating tasks in `TASKS.md`.
- Filling `nezjištěno` fields by guessing; inventing numeric targets.
- Writing `schvaleno` or any `DEC-*` approval before the human grants it.
- Resolving contradictions silently – record them as `Q-*` and ask.

## Stop points

Stop and hand over to the human when:

1. A coherent first-increment scope is written → present it as a list of
   IDs and ask for approval of **exactly that list**. On approval, create
   `DEC-*` of type `schvaleni-rozsahu` per `AGENTS.md` 4.3 and set the
   listed records to `schvaleno` with the DEC reference.
2. A blocking contradiction or unknown needs a human decision.
3. The human asks to pause → update `PROJECT.md` "Bod pokračování".

## Handover output (in Czech)

- Summary of understanding (3–8 bullets).
- IDs written this session, grouped by type.
- Open questions `Q-*` that block approval vs. those that do not.
- Explicit question: approve scope `[IDs]` or continue discovery?
- After approval: pointer to `/plan-increment`.
