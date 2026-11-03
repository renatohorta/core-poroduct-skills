# Data Dictionary — Core Product Skills

> Updated 2026-11-03.

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
| `.context/inbox/{initiatives,tasks,bugs,tech-debt}/` | Raw intake (drafts) | manual / agent |
| `.context/kanban/{1-backlog..7-done,blocked}/` | Task cards (`.md` + YAML frontmatter) | manual (`git mv` between columns) |
| `.context/tracking/progress.md` | Overall progress | maintainer / coding agent |
| `.context/tracking/decisions.md` | ADR record | any agent |

### Kanban card schema (`.context/kanban/{column}/{ID}.md`)

```yaml
---
id: TASK-001
title: Task title
status: ready          # backlog|ready|todo|doing|review|testing|staging|done|blocked
priority: medium
assignee:
created_at: 2026-01-01T00:00:00
updated_at: 2026-01-01T00:00:00
tags: []
type: task             # task|bug|tech-debt|initiative
source: inbox/bugs/foo.md
---
```

### Executable issue schema (`.context/kanban/2-todo/{ID}.md`)

When a card is promoted to `2-todo/`, it is refined into an executable issue
with: Contexto & Objetivo, Arquivos Alvo, Critérios de Aceite (DoR/DoD),
Insumos Técnicos e Contratos de Dados, and Passos de Validação e Execução.

### Skill artifacts (mandatory in `.context/` — ADR-0011)

| Path | Content | Written by |
|------|---------|-----------|
| `.context/docs/<NN-phase>/rup-<skill>.md` | Frontmatter (skill, discipline, phase, milestone, generated_at) + briefing excerpt + the host's document; regenerated per run | every `rup-*` skill |
| `.context/docs/<NN-phase>/rup-orchestrator-sizing.md` | UCP table + JSON | `rup-orchestrator --estimate` |
| `.context/tracking/rup-log.md` | Append-only table: when, phase, skill, artifact | every write |

## Persistence rules

- `.context/` is the **single source of truth**; `.hermes/`/`.claude/` are forbidden.
- The kanban column (folder) must match the card's `status:` frontmatter.
- No secrets in committed files; `.env` stays at the root and is git-ignored.

## Decisions

- Filesystem-as-database: no DB engine, no migrations — the structure IS the schema.
