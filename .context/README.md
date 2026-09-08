# .context/ — Project Source of Truth

**Project**: Core Product Skills — canonical repository of the `cp-*` skills of
the Software Factory (CrewAI), propagated to the **Hermes Agent** and **Claude Code**.

This directory is the **single source of truth** for the project context. All
agents must read and write context here, **never** in `.hermes/` or `.claude/`.

## Where to start

| I want to… | Read |
|------------|------|
| Understand the product | `docs/01-inception/vision-and-scope.md` |
| Know what the system does and what is missing | `docs/01-inception/requirements.md` |
| Understand how it works internally | `docs/02-elaboration/architecture.md` |
| See the API/CLI contracts | `docs/03-construction/api-contracts.md` |
| Install/operate/debug | `docs/04-transition/devops-infra.md` |
| See what is in the queue | `docs/06-kanban.md`, `kanban/` |
| Know why something is the way it is | `tracking/decisions.md` |

## Structure

### docs/ — RUP Operational (4 phases)

| Phase | File | Content | Skill that writes |
|-------|------|---------|-------------------|
| `01-inception/` | `vision-and-scope.md` | Product vision, actors, business goals | `cp-software-spec` |
| `01-inception/` | `requirements.md` | FR + NFR (incl. security/LGPD) | `cp-requirements`, `cp-competitive-analysis`, `cp-security` |
| `02-elaboration/` | `architecture.md` | Stack, C4/Mermaid, structural decisions | `cp-architecture`, `cp-implementation`, `cp-maintenance` |
| `02-elaboration/` | `domain-model.md` | Domain entities, aggregates, use cases | `cp-software-spec` |
| `03-construction/` | `api-contracts.md` | OpenAPI/CLI contracts, endpoints, schemas | `cp-software-spec` |
| `03-construction/` | `ui-spec.md` | Routes, Design System, AppShell, Generative UI | `cp-software-spec` |
| `03-construction/` | `data-dictionary.md` | DB models, migrations, persistence rules | `cp-software-spec` |
| `04-transition/` | `test-strategy.md` | Test pyramid, coverage, commands | `cp-testing`, `cp-quality`, `cp-bug-fix` |
| `04-transition/` | `devops-infra.md` | Docker, CI/CD, variables, runbooks | `cp-devops`, `cp-goal-loop` |
| `06-kanban.md` | — | Kanban/pipeline state | `cp-agile` |

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
When a card is promoted to `2-todo/`, it is refined into an **executable issue**
(Ready for Dev) with DoR, API contracts, schemas and target files — see
`kanban/2-todo/{ID}.md`. Details in `kanban/README.md`.

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
