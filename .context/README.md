# .context/ — Project Source of Truth

**Project**: Core Product Skills — canonical repository of the `rup-*` skills
(Rational Unified Process; the agent running a skill is the LLM — ADR-0012),
propagated to the **Hermes Agent**
and **Claude Code**. The legacy `cp-*` family was removed (ADR-0010).

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

The project context of **this repository**, organized by RUP phase. The files
below are curated by whoever changes the repository (human or coding agent).

When a `rup-*` skill runs against a project, it **always** writes its artifact
next to them as `docs/<NN-phase>/rup-<skill>.md` and logs it in
`tracking/rup-log.md` (ADR-0011) — the `rup-` prefix keeps generated artifacts
apart from the curated docs, which the skills never overwrite.

| Phase | File | Content |
|-------|------|---------|
| `01-inception/` | `vision-and-scope.md` | Product vision, actors, scope |
| `01-inception/` | `requirements.md` | FR + NFR (incl. security/LGPD) |
| `02-elaboration/` | `architecture.md` | Components, dispatch, structural decisions |
| `02-elaboration/` | `domain-model.md` | Entities (skill, role, packet, artifact, card), use cases |
| `03-construction/` | `api-contracts.md` | CLI contracts of the skills |
| `03-construction/` | `ui-spec.md` | CLI surface and conventions |
| `03-construction/` | `data-dictionary.md` | Filesystem structures, kanban schema |
| `04-transition/` | `test-strategy.md` | Test levels, coverage, commands |
| `04-transition/` | `devops-infra.md` | Install, CI, runbook |
| `06-kanban.md` | — | Kanban state |

### inbox/ — Work intake
One `.md` file per item.

- `initiatives/` — Product initiatives
- `tasks/` — Tasks
- `bugs/` — Bugs
- `tech-debt/` — Technical debt
- `processed/` — Resolved items (history)

### tracking/ — Tracking
- `progress.md` — Overall progress and next steps
- `rup-log.md` — One line per artifact written by the `rup-*` skills (created on first run)
- `decisions.md` — Decision log (ADR-0001 … ADR-0011)

### kanban/ — Execution pipeline (managed by hand)
Source of truth for the task flow; Trello, when connected, is only a
mirror. A task is a `.md` with YAML frontmatter and the column is the folder:
`1-backlog/` → `2-todo/` → `3-doing/` → `4-review/` → `5-testing/` →
`6-staging/` → `7-done/`, plus `blocked/` for questions and blockers.

Raw items enter `inbox/`; after triage, they become tasks in `kanban/1-backlog/`.
When a card is promoted to `2-todo/`, it is refined into an **executable issue**
(Ready for Dev) with DoR, API contracts, schemas and target files — see
`kanban/2-todo/{ID}.md`. Details in `kanban/README.md`.

## Rules

1. Every change to the repository updates the affected file in `docs/`, per
   the map above.
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
