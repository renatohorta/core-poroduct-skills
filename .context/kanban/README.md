# kanban/ — Execution Pipeline

Source of truth for the task flow, managed by `rup-backlog` (and the execution
skills that call the same move logic). When Trello is configured, it is only a
**mirrored view** — what matters is what is here. Writing needs the RUP standard
authorized in `.context/` (marker `.rup-standard`, exit 5 otherwise).

## Relationship with `../inbox/`

`inbox/` is raw intake: a draft of an initiative, task, bug or technical debt.
After triage, the item becomes a card here, in `1-backlog/`, created with
`rup-backlog --new` (or derived from the requirements with `--derive`).

## Columns

| Folder | Meaning |
|--------|---------|
| `1-backlog/` | Triaged work; every new card starts here |
| `2-todo/` | Prioritized, waiting for execution |
| `3-doing/` | In execution |
| `4-review/` | Delivered, waiting for review |
| `5-testing/` | Review approved, in testing |
| `6-staging/` | Staging |
| `7-done/` | Done |
| `blocked/` | Question or blocker waiting for a human answer |

A card's `status:` always equals its folder (the folder wins).

## Cards

One file per card: `.context/kanban/<column>/<ID>.md`, frontmatter + sections.
IDs are assigned by the skill (3 digits, one sequence per type).

| Type | ID | Parent | Required sections |
|------|----|--------|-------------------|
| epic | `EP-NNN` | none | Goal, Scope |
| story | `ST-NNN` | epic | User story, Acceptance criteria, Definition of Done |
| task | `TK-NNN` | story | Description, Target files, Covers |
| bug | `BUG-NNN` | story (optional) | Symptom, Reproduction (then Root cause, Fix, Regression test) |

- Acceptance criteria get IDs `ST-NNN/AC-n`; a task's `## Covers` lists them.
- `## History` is always the last section: `- <iso> <from> → <to> — <reason> (<actor>)`.
- `rup-build --finish` adds `## Delivery` (its headings demoted); `rup-review`
  adds `## Review`.
- Priority is MoSCoW: `Must`, `Should` (default), `Could`, `Won't`.

```markdown
---
id: ST-001
type: story
title: Book a slot
status: 1-backlog
parent: EP-001
priority: Should
source: rup-requirements#UC-01
created_at: 2026-11-03T10:00:00
updated_at: 2026-11-03T10:00:00
---

# ST-001 — Book a slot

## User story
## Acceptance criteria
- **ST-001/AC-1**: ...
## Definition of Done
## History
```

## Commands (`rup-backlog`, `rup-build`, `rup-debug`, `rup-review`)

```
rup-backlog --new {epic,story,task} --title T --doc FILE|- [--parent ID]
rup-backlog --list | --show ID | --derive
rup-backlog --move ID COLUMN --reason "..."     # declaration is enough; any move is legal
rup-backlog --release-new / --iteration-new / --plan EP --iteration I / --roadmap
rup-build   --start TK-NNN | --finish TK-NNN --delivery FILE|-
rup-debug   --open ... | --diagnose BUG-NNN --doc FILE|-
rup-review  TK-NNN | --record TK-NNN --doc FILE|-
```

Stories and epics move by roll-up: to `3-doing` when the first child starts, to
`7-done` when all children are done. A forward jump over columns only adds a
warning to History. Every move is logged in `tracking/rup-log.md` and
regenerates `docs/06-roadmap.md` and `docs/06-board.md` (generated, never edited;
the curated `docs/06-kanban.md` is not touched).

Cards written with the old schema (`TASK-NNN`, `task|bug|tech-debt|initiative`)
are not migrated automatically.
