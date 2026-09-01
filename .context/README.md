# .context/ — Project Source of Truth

**Project**: Core Product Skills — canonical repository of the `cp-*` skills of
the Software Factory (CrewAI), propagated to the **Hermes Agent** and **Claude Code**.

This directory is the **single source of truth** for the project context. All
agents must read and write context here, **never** in `.hermes/` or `.claude/`.

## Where to start

| I want to… | Read |
|------------|------|
| Understand the product | `docs/00-vision.md` |
| Know what the system does and what is missing | `docs/01-requirements.md` |
| Understand how it works internally | `docs/02-architecture.md` |
| Install/operate/debug | `docs/05-devops-operations.md` |
| See what is in the queue | `docs/06-kanban.md`, `kanban/` |
| Know why something is the way it is | `tracking/decisions.md` |

## Structure

### docs/ — Engineering disciplines
| File | Discipline | Skill that writes |
|------|-----------|-------------------|
| `00-vision.md` | Product vision | `cp-doc-initializer` |
| `01-requirements.md` | Requirements | `cp-requirements`, `cp-competitive-analysis` |
| `02-architecture.md` | Architecture | `cp-architecture`, `cp-implementation`, `cp-maintenance` |
| `03-security-lgpd.md` | Security/LGPD | `cp-security` |
| `04-quality-qa.md` | Quality/QA | `cp-testing`, `cp-documentation`, `cp-quality`, `cp-bug-fix` |
| `05-devops-operations.md` | DevOps/Operations | `cp-devops`, `cp-goal-loop` |
| `06-kanban.md` | Kanban/pipeline | `cp-agile` |

### inbox/ — Work intake
One `.md` file per item.

- `initiatives/` — Product initiatives
- `tasks/` — Tasks
- `bugs/` — Bugs (`DT-01`, `DOC-01`)
- `tech-debt/` — Technical debt (`DT-02` … `DT-06`)

### tracking/ — Tracking
- `progress.md` — Overall progress and next steps
- `decisions.md` — Decision log (ADR-0001 … ADR-0006)

### kanban/ — Execution pipeline (`cp-agile`)
Source of truth for the task flow; Trello, when connected, is only a
mirror. A task is a `.md` with YAML frontmatter and the column is the folder:
`1-backlog/` → `2-todo/` → `3-doing/` → `4-review/` → `5-testing/` →
`6-staging/` → `7-done/`, plus `blocked/` for questions and blockers.

Raw items enter `inbox/`; after triage, they become tasks in `kanban/1-backlog/`.
Details in `kanban/README.md`.

## Rules

1. Every `cp-*` skill documents its artifacts in `docs/`, per the map above.
2. New work enters through `inbox/`, not directly in `docs/`; once triaged,
   it moves to `kanban/1-backlog/`.
3. A relevant decision becomes an ADR in `tracking/decisions.md` — with context
   and consequences, not just the conclusion.
4. In a divergence between `.context/` and `docs/` (the repository's human
   documentation), **`.context/` prevails**.

## Relationship with `docs/` at the root

`docs/` (`ARCHITECTURE.md`, `INSTALLATION.md`, `SKILLS.md`) is presentation
documentation, aimed at human readers. `.context/` is the operational context,
aimed at agents — it includes real state, gaps and pending items.
