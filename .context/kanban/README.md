# kanban/ — Execution Pipeline

Source of truth for the task flow, managed by the `cp-agile` skill. When Trello
is configured, it is only a **mirrored view** — what matters is what is here.

## Relationship with `../inbox/`

`inbox/` is raw intake: a draft of an initiative, task, bug or technical debt.
After triage, the item becomes a task here, in `1-backlog/`, with `status:`
filled in — move it with `git mv` to preserve history.

## Columns

| Folder | Meaning |
|--------|---------|
| `1-backlog/` | Intake. The daemon scans here for tasks with `status: ready` |
| `2-todo/` | Prioritized, waiting for execution. **Cards here are executable issues (Ready for Dev)** |
| `3-doing/` | In execution (dispatched to the `cp-orchestrator`) |
| `4-review/` | Waiting for review |
| `5-testing/` | In testing |
| `6-staging/` | Staging |
| `7-done/` | Done |
| `blocked/` | Question or blocker waiting for a human answer |

## Backlog → ToDo promotion (executable issue)

When a card is promoted from `1-backlog/` to `2-todo/`, it is transformed and
validated as an **Issue Executável (Ready for Dev)** with Definition of Ready
(DoR), API contracts, schemas and target files. Use the `cp-software-spec`
skill:

```bash
python <skills>/cp-software-spec/scripts/run.py --refine-card TASK-001
```

## Task format

One `.md` file per task, with YAML frontmatter. The `status:` field must
match the folder the file is in.

```markdown
---
id: TASK-001
title: Task title
status: ready
priority: medium
assignee:
created_at: 2026-01-01T00:00:00
updated_at: 2026-01-01T00:00:00
tags: []
---

# Task title

## Description

## Acceptance Criteria

- [ ] ...
```

Valid `status:` values: `backlog`, `ready`, `todo`, `doing`, `review`, `testing`,
`staging`, `done`, `blocked`. Only `ready` in `1-backlog/` is dispatched.

## Commands

```bash
# Monitor the backlog and dispatch tasks
python <skills>/cp-agile/scripts/run.py --daemon

# Document the current kanban state in ../docs/06-kanban.md
python <skills>/cp-agile/scripts/run.py --doc
```
