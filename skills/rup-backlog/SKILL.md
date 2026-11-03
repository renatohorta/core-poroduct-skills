---
name: rup-backlog
description: "Create and inspect kanban cards (epics, stories, tasks) in the project's .context/kanban/. Use when the user wants to add backlog items, break an epic into stories or a story into tasks, or list/show cards."
---

# rup-backlog — kanban cards

Cards live one per file in `.context/kanban/<column>/<ID>.md`. IDs (`EP-001`,
`ST-001`, `TK-001`) are assigned by the skill, never by you. Needs the RUP
standard authorized in `.context/` (exit 5 otherwise: see `rup-context`).

## Steps

1. Write a document with the card's `## ` sections (see `references/cards.md`).
   Do not write `## History`; the skill adds it.
2. Create the card: `python scripts/run.py --new story --title "..." --doc FILE|- --parent EP-001`.
   It prints the new ID. Stories get numbered criteria `ST-NNN/AC-n`; a task's
   `## Covers` must list criteria of its parent story.
3. Inspect with `--list` and `--show ID`.
4. Move cards as work progresses: `--move ID COLUMN --reason "..."`. Declaring is
   enough; skipping columns only warns in the card's History. A story/epic moves
   by itself (roll-up): to `3-doing` when its first child starts, to `7-done`
   when all children are done.

## Commands

- `--new {epic,story,task} --title T --doc FILE|- [--parent ID] [--priority P] [--source S]`
- `--move ID COLUMN --reason R` — move a card (reason required; logged).
- `--show ID` — print the card file.
- `--list [--column C] [--type T]` — table `ID | Type | Title | Column | Parent`.
- `--context-dir D` — another `.context/` (default: auto-detect or `RUP_CONTEXT_DIR`).

Exit codes: 0 ok · 1 invalid document/usage · 4 not writable · 5 not authorized.
