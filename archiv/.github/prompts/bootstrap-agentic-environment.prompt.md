---
name: bootstrap-agentic-environment
description: 'Create or update a technology-neutral project environment for human–agent development: rules, records, lifecycle, entry prompts. Copies templates; does NOT specify or implement the application.'
argument-hint: 'Target directory (default: workspace root), documentation language (default: cs), mode: propose | write (default: propose). No application description needed.'
agent: agent
---

# Bootstrap agentic environment

You are setting up a **working system**, not an application. The result must
work in a fresh session without this prompt or this chat.

## Language

- Talk to the human in **Czech**.
- Templates are already written in Czech with full diacritics. Do not
  translate, rewrite, or "improve" their wording.
- Identifiers, state slugs, anchors and file names stay ASCII as in templates.

## Hard rules

1. Write only Markdown files listed in step 3. Nothing else.
2. Do not ask about the application, its domain, users, or technology stack.
   If the human volunteers it, record it verbatim in `SPEC.md` → "Předpoklady"
   with origin "člověk, bootstrap", nothing more.
3. Do not install, run, commit, push, create repositories, or enable hooks/CI.
4. Do not invent tasks, requirements, decisions, approvals, or test results.
5. Never overwrite a file that already contains real records or edited text.
   Propose a diff instead.
6. If you lack access to write, deliver a clearly labelled **proposal**, not
   a claim of a created environment.
7. Finishing bootstrap does **not** start discovery. Stop at step 6.

## Step 1 – Collect settings (one question at a time, only if unknown)

Apply defaults silently when the argument or workspace makes them obvious:

| Setting | Default | Ask only if |
| --- | --- | --- |
| Target directory | Workspace root | Several candidate roots exist. |
| Documentation language | `cs` (Czech) | Human wrote in another language. |
| Mode | `propose` | Human did not say "write / vytvoř / zapiš". |
| Approver (`{{APPROVER}}`) | The human you talk to | Human mentions a different person/role. |
| Project name | Directory name | Directory name is generic (`src`, `app`, `tmp`). |

Do not ask anything else. Unknown operational preferences go into
`PROJECT.md` → "Otevřené otázky" as `Q-*` only if they block safe writing
(they rarely do).

## Step 2 – Inspect target

Read only: existing `README.md`, `AGENTS.md`, `PROJECT.md`, `SPEC.md`,
`TASKS.md`, `DECISIONS.md`, `IDEAS.md`, `.github/prompts/*.prompt.md`,
`.github/copilot-instructions.md`. Do not scan the whole repository.

Classify the target:

- **Empty** – none of the above exist → full copy.
- **Partial** – some exist → copy only missing files; for existing files list
  what the template has and the file lacks; propose additions only.
- **Existing project** – `PROJECT.md` has a phase other than
  `pripraveno-ke-specifikaci` or `TASKS.md`/`DECISIONS.md` contain records →
  never change phase, IDs, states, approvals or records. Propose only rule
  migrations as a diff for human review.
- If `.github/copilot-instructions.md` already holds project rules, keep it as
  the single rules source: do not create a competing `AGENTS.md`; instead
  propose adding a link from it to the templates' process sections.

## Step 3 – Produce files

Source templates (relative to this prompt's repository):

| Template | Target |
| --- | --- |
| `.github/templates/agentic/AGENTS.md` | `<target>/AGENTS.md` |
| `.github/templates/agentic/README.md` | `<target>/README.md` |
| `.github/templates/agentic/PROJECT.md` | `<target>/PROJECT.md` |
| `.github/templates/agentic/SPEC.md` | `<target>/SPEC.md` |
| `.github/templates/agentic/TASKS.md` | `<target>/TASKS.md` |
| `.github/templates/agentic/DECISIONS.md` | `<target>/DECISIONS.md` |
| `.github/prompts/discover-project.prompt.md` | `<target>/.github/prompts/discover-project.prompt.md` |
| `.github/prompts/plan-increment.prompt.md` | `<target>/.github/prompts/plan-increment.prompt.md` |
| `.github/prompts/work-task.prompt.md` | `<target>/.github/prompts/work-task.prompt.md` |

Integration rule (deterministic):

- Tool is VS Code + GitHub Copilot → use `.github/prompts/` as above.
- Any other tool → place the three entry prompts in `<target>/docs/workflows/`
  without the `.prompt` suffix and strip the frontmatter. Update the
  "Jak začít" section of `README.md` accordingly. Never create both variants.

Placeholder substitution – replace **only** these tokens:

- `{{PROJECT_NAME}}` → project name
- `{{LANGUAGE}}` → documentation language name in Czech (e.g. `čeština`)
- `{{APPROVER}}` → approver name or role
- `{{DATE}}` → today's date `YYYY-MM-DD`

Do not change anything else in the templates. Do not create `IDEAS.md`,
`docs/ARCHITECTURE.md` or other optional files.

If the kit's own root `README.md` is the target and it contains the marker
`<!-- agentic-starter-kit -->`, it is kit documentation and may be replaced
by the template.

Mode `propose`: show the file list with one-line purpose each and the exact
placeholder values, then **STOP and wait** for explicit "write".
Mode `write`: create the files, then continue.

## Step 4 – Set phase

Only after all files from step 3 exist:

- Empty/partial target → `PROJECT.md` phase `pripraveno-ke-specifikaci`, date today.
- Anything prevented completion → phase `bootstrap-neuplny`, with the concrete
  obstacle and the next safe step in "Bod pokračování".
- Existing project → do not touch the phase.

## Step 5 – Verify (report each item as OK / FAIL / NOT CHECKED)

1. All target files from step 3 exist; no other files were created.
2. Every relative link and anchor in the created files resolves.
3. Every placeholder is substituted (search for `{{`).
4. `TASKS.md`, `DECISIONS.md`, `SPEC.md` contain no real records – only
   sections marked as "Vzor".
5. `PROJECT.md` phase matches step 4.
6. Entry prompts have valid frontmatter (`name`, `description`,
   `argument-hint`, `agent`) and are in the location chosen by the
   integration rule.

Static documentation check only. Do not claim the agent workflow was tested.

## Step 6 – Report and stop

Output, in Czech:

- Created / updated / proposed files (three separate lists).
- Verification results from step 5.
- Unverified assumptions and open items.
- Exact next action for the human: `/discover-project` (or the manual
  equivalent for non-VS Code tools).

Then stop. Do not start a product conversation, suggest a stack, or create
tasks.
