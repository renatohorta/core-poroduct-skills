---
name: cp-backlog
description: "Create and inspect kanban cards (epics, stories, tasks) in the project's .context/kanban/. Use when the user wants to add backlog items or cards, break an epic into stories or a story into tasks, move a card, plan an iteration, manage releases or the roadmap, derive epics/stories from requirements, or list/show cards."
---

# cp-backlog — kanban cards

Cards live one per file in `.context/kanban/<column>/<ID>.md`. IDs (`EP-001`,
`ST-001`, `TK-001`) are assigned by the skill, never by you. Needs the RUP
standard authorized in `.context/` (exit 5 otherwise: see `cp-context`).

## Steps

1. Write a document with the card's `## ` sections (see `references/cards.md`).
   Do not write `## History`; the skill adds it.
2. Create the card: `python scripts/run.py --new story --title "..." --doc FILE|- --parent EP-001`.
   It prints the new ID. Stories get numbered criteria `ST-NNN/AC-n`; a task's
   `## Covers` must list criteria of its parent story.
3. Derive from requirements: `--derive`, then create only the pending ones (`--source "cp-requirements#<heading>"`).
4. Inspect with `--list` and `--show ID`.
5. Move cards as work progresses: `--move ID COLUMN --reason "..."`. Declaring is
   enough; skipping columns only warns in the card's History. A story/epic moves
   by itself (roll-up): to `3-doing` when its first child starts, to `7-done`
   when all children are done.
6. Plan: `--release-new --title T`, `--iteration-new --release R1 --phase P --goal G`,
   `--plan EP-001 --iteration R1-I1`. `docs/06-roadmap.md` and `docs/06-board.md`
   are generated views (regenerated after every change; never edit them).

## Commands

- `--new {epic,story,task} --title T --doc FILE|- [--parent ID] [--priority P] [--source S]`
- `--move ID COLUMN --reason R` — move a card (reason required; logged).
- `--show ID` — print the card file.
- `--list [--column C] [--type T]` — table `ID | Type | Title | Column | Parent`.
- `--release-new --title T [--milestone M] [--goal G] [--target-date D]` — prints `R<n>`.
- `--iteration-new --release R --phase P --goal G [--start S] [--end E]` — prints `R<n>-I<m>`.
- `--plan EPIC --iteration I` — plan an epic into an iteration.
- `--derive [--phase P]` — read-only: shows `cp-requirements`, existing cards, `Already derived` / `Not yet derived` / `Orphan cards`, and the exact `--new` command per pending use-case package (epic) and use case (story). Exit 1 if requirements are not recorded.
- `--roadmap` — regenerate the two views.
- `--context-dir D` — another `.context/` (default: auto-detect or `RUP_CONTEXT_DIR`).

Exit codes: 0 ok · 1 invalid document/usage · 4 not writable · 5 not authorized.
