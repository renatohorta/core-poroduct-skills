# .context/ — Project Source of Truth

**Project**: Core Product Skills — canonical repository of the `cp-*` skills
(Rational Unified Process; the agent running a skill is the LLM — ADR-0012),
propagated to the **Hermes Agent**
and **Claude Code**: 9 document skills + 6 execution skills (ADR-0013). The
legacy Software Factory family (removed in ADR-0010) also used the `cp-` prefix;
the current `cp-*` skills are the RUP skills, renamed from `rup-*` (ADR-0014).

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
| See what is in the queue | `docs/06-board.md` (generated), `docs/06-kanban.md`, `kanban/` |
| See the roadmap | `docs/06-roadmap.md` (generated), `roadmap/` |
| Know why something is the way it is | `tracking/decisions.md` |

## Structure

### docs/ — RUP Operational (4 phases)

The project context of **this repository**, organized by RUP phase. The files
below are curated by whoever changes the repository (human or coding agent).

When a `cp-*` skill runs against a project, it **always** writes its artifact
next to them as `docs/<NN-phase>/cp-<skill>.md` and logs it in
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
| `06-kanban.md` | — | Kanban state (curated, never touched by the skills) |
| `06-roadmap.md` | — | Roadmap view, **generated** by `cp-backlog` (do not edit) |
| `06-board.md` | — | Board by column, **generated** by `cp-backlog` (do not edit) |

### inbox/ — Work intake
One `.md` file per item.

- `initiatives/` — Product initiatives
- `tasks/` — Tasks
- `bugs/` — Bugs
- `tech-debt/` — Technical debt
- `processed/` — Resolved items (history)

### tracking/ — Tracking
- `progress.md` — Overall progress and next steps
- `rup-log.md` — One line per artifact written by the `cp-*` skills (created on first run)
- `decisions.md` — Decision log (ADR-0001 … ADR-0016)

### kanban/ — Execution pipeline (cards managed by `cp-backlog`)
Source of truth for the task flow; Trello, when connected, is only a
mirror. A card is a `.md` with YAML frontmatter and the column is the folder:
`1-backlog/` → `2-todo/` → `3-doing/` → `4-review/` → `5-testing/` →
`6-staging/` → `7-done/`, plus `blocked/` for questions and blockers.
Card types: epic `EP-NNN`, story `ST-NNN`, task `TK-NNN`, bug `BUG-NNN`; IDs are
assigned by the skill. Cards move with `cp-backlog --move ID COLUMN --reason R`
(declaration is enough) and `cp-build`/`cp-debug`/`cp-review` move them at
their natural steps. Details in `kanban/README.md`.

### roadmap/ — Releases and iterations
`R<n>.md` (release) and `R<n>-I<m>.md` (iteration, with a RUP phase), created by
`cp-backlog`. The generated views `docs/06-roadmap.md` and `docs/06-board.md`
show releases → iterations → epics → story progress.

### Authorization marker
`.rup-standard` (version, who authorized, when). Without it no skill writes into
`.context/` (exit 5); `cp-context --init` adds it after the user approves
(ADR-0013). **This repository's own `.context/` has no marker yet** — run
`cp-context --status` and, with the owner's approval, `--init`.

## Rules

1. Every change to the repository updates the affected file in `docs/`, per
   the map above.
2. New work enters through `inbox/`, not directly in `docs/`; once triaged,
   it becomes a card in `kanban/1-backlog/` (`cp-backlog --new`).
3. A relevant decision becomes an ADR in `tracking/decisions.md` — with context
   and consequences, not just the conclusion.
4. `.context/` is the only documentation of the project (the root `docs/`
   was removed, ADR-0015). Human-facing entry points are `README.md` and
   `skills/README.md`; everything else lives here.
