# Data Dictionary — Core Product Skills

> Document managed by the `cp-software-spec` skill. Updated 2026-09-07.

## Status

- [x] In progress (derived from the existing code)

## Overview

This repository has **no database**. The "data" is the **filesystem state**:
`.context/` (the source of truth) and the pipeline `outputs/`. This file
documents the persistent structures that agents read/write.

## Persistent structures

### `.context/` — source of truth

| Path | Content | Written by |
|------|---------|-----------|
| `.context/README.md` | Index + system prompt for agents | `cp-software-spec` |
| `.context/docs/01-inception/` | Vision, requirements | `cp-software-spec`, `cp-requirements` |
| `.context/docs/02-elaboration/` | Architecture, domain model | `cp-software-spec`, `cp-architecture` |
| `.context/docs/03-construction/` | API contracts, UI spec, data dictionary | `cp-software-spec` |
| `.context/docs/04-transition/` | Test strategy, devops infra | `cp-software-spec`, `cp-testing`, `cp-devops` |
| `.context/inbox/{initiatives,tasks,bugs,tech-debt}/` | Raw intake (drafts) | manual / agent |
| `.context/kanban/{1-backlog..7-done,blocked}/` | Task cards (`.md` + YAML frontmatter) | `cp-agile` |
| `.context/tracking/progress.md` | Overall progress | orchestrator |
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

### Pipeline outputs (`skills/deprecated/cp-orchestrator/outputs/`)

| Path | Content |
|------|---------|
| `pipeline_<timestamp>/<phase>.md` | Per-phase artifact |
| `pipeline_<timestamp>/pipeline_report.json` | Structured report |

## Persistence rules

- `.context/` is the **single source of truth**; `.hermes/`/`.claude/` are forbidden.
- The kanban column (folder) must match the card's `status:` frontmatter.
- `outputs/` is disposable and git-ignored.
- No secrets in committed files; `.env` stays at the root and is git-ignored.

## Decisions

- Filesystem-as-database: no DB engine, no migrations — the structure IS the schema.
