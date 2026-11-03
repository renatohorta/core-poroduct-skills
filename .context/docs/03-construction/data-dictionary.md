# Data Dictionary — Core Product Skills

> Updated 2026-11-03 (cards, roadmap, marker — ADR-0013).

## Status

- [x] In progress (derived from the existing code)

## Overview

This repository has **no database**. The "data" is the **filesystem state**:
`.context/` (the source of truth), including the artifacts the skills record. This file
documents the persistent structures that agents read/write.

## Persistent structures

### `.context/` — source of truth

| Path | Content | Written by |
|------|---------|-----------|
| `.context/README.md` | Index + system prompt for agents | maintainer / coding agent |
| `.context/docs/01-inception/` | Vision, requirements | maintainer / coding agent |
| `.context/docs/02-elaboration/` | Architecture, domain model | maintainer / coding agent |
| `.context/docs/03-construction/` | API contracts, UI spec, data dictionary | maintainer / coding agent |
| `.context/docs/04-transition/` | Test strategy, devops infra | maintainer / coding agent |
| `.context/.rup-standard` | Authorization marker: `version`, `authorized_by`, `authorized_at` | `cp-context --init` |
| `.context/inbox/{initiatives,tasks,bugs,tech-debt,processed}/` | Raw intake (drafts) | manual / agent |
| `.context/kanban/{1-backlog..7-done,blocked}/` | Cards `EP/ST/TK/BUG-NNN` (`.md` + frontmatter) | `cp-backlog`, `cp-build`, `cp-debug`, `cp-review` |
| `.context/roadmap/R<n>.md`, `R<n>-I<m>.md` | Releases and iterations | `cp-backlog` |
| `.context/docs/06-roadmap.md`, `06-board.md` | Generated views (never edited) | `cp-backlog` |
| `.context/tracking/progress.md` | Overall progress | maintainer / coding agent |
| `.context/tracking/decisions.md` | ADR record | any agent |

### Card schema (`.context/kanban/{column}/{ID}.md`)

```yaml
---
id: ST-001             # EP-NNN | ST-NNN | TK-NNN | BUG-NNN (assigned by the skill)
type: story            # epic | story | task | bug
title: Single-line title      # not of the form [..]
status: 1-backlog      # always equal to the folder
parent: EP-001         # story -> epic, task -> story, bug -> story (optional)
priority: Should       # MoSCoW: Must | Should | Could | Won't
source: cp-requirements#UC-01   # RUP artifact + section (single line)
created_at: 2026-11-03T10:00:00
updated_at: 2026-11-03T10:00:00
---
```

Epics also carry `release` and `iteration` (set by `--plan`); a task/bug in
execution carries `branch` (set by `cp-build --start`).

| Type | Required sections (before `## History`) |
|------|------------------------------------------|
| epic | Goal, Scope |
| story | User story, Acceptance criteria (`- **ST-NNN/AC-n**: text`), Definition of Done |
| task | Description, Target files, Covers (`ST-NNN/AC-n` of the parent story) |
| bug | Symptom, Reproduction; then Root cause (`cp-debug --diagnose`), Fix, Regression test |

Added by the skills: `## Delivery` (`cp-build --finish`, delivery headings
demoted one level), `## Review` (`cp-review`, earlier reviews kept) and
`## History`, always the last section: `- <iso> <from> → <to> — <reason> (<actor>)`.

### Roadmap files (`.context/roadmap/`)

| File | Frontmatter |
|------|-------------|
| `R<n>.md` | `id, title, milestone` (empty or a RUP milestone), `goal, target_date` |
| `R<n>-I<m>.md` | `id, release, phase` (a RUP phase), `goal, start, end` |

### Skill artifacts (mandatory in `.context/` — ADR-0011)

| Path | Content | Written by |
|------|---------|-----------|
| `.context/docs/<NN-phase>/cp-<skill>.md` | Frontmatter (skill, discipline, phase, milestone, generated_at) + briefing excerpt + the host's document; regenerated per run | every `cp-*` skill |
| `.context/docs/<NN-phase>/cp-orchestrator-sizing.md` | UCP table + JSON | `cp-orchestrator --estimate` |
| `.context/docs/01-inception/cp-discover.md` | Discovery record (Problem … Open questions) | `cp-discover --record` |
| `.context/tracking/rup-log.md` | Append-only table: when, phase, skill, artifact; also card creations, moves, imports | every write |

## Persistence rules

- `.context/` is the **single source of truth**; `.hermes/`/`.claude/` are forbidden.
- The kanban column (folder) must match the card's `status:` frontmatter.
- No skill writes into `.context/` without the `.rup-standard` marker (exit 5);
  curated docs, imported originals and `docs/06-kanban.md` are never overwritten.
- No secrets in committed files; `.env` stays at the root and is git-ignored.

## Decisions

- Filesystem-as-database: no DB engine, no migrations — the structure IS the schema.
