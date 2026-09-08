# Domain Model — Core Product Skills

> Document managed by the `cp-software-spec` skill. Updated 2026-09-07.

## Status

- [x] In progress (derived from the existing code)

## Core entities

The Software Factory is a set of **skills** orchestrated by a **pipeline**.
There is no persistent domain model in the traditional sense — the "entities"
are the artifacts and the flow between them.

| Entity | Description | Where it lives |
|--------|-------------|----------------|
| **Skill** (`cp-*`) | A self-contained unit: `SKILL.md` + `scripts/run.py` + `references/` | `skills/cp-<name>/` |
| **Crew** | A CrewAI crew embedded in a skill's `run.py` | `skills/cp-<name>/scripts/run.py` |
| **Phase artifact** | The output of a pipeline phase, passed to the next | `cp-orchestrator/outputs/pipeline_<ts>/` |
| **Kanban card** | A task `.md` with YAML frontmatter; the column is the folder | `.context/kanban/{column}/{ID}.md` |
| **Executable issue** | A refined card in `2-todo/` (Ready for Dev) | `.context/kanban/2-todo/{ID}.md` |
| **ADR** | Architecture Decision Record | `.context/tracking/decisions.md` |

## Aggregates

- **Pipeline** aggregates the 8 phase crews (requirements → architecture →
  implementation → testing → security → devops → documentation → quality) and
  applies a quality gate (PASS/WARN/FAIL) between them.
- **Kanban** aggregates cards across columns; `cp-agile` is the aggregate root
  that scans `1-backlog/` for `status: ready` and dispatches to the orchestrator.

## Core use cases

1. **Initialize a project's context** — `cp-software-spec --init` scaffolds
   `.context/` (RUP 4 phases + kanban + tracking).
2. **Reverse-engineer a codebase** — `cp-software-spec --inspect <path>`
   produces RUP docs from the existing code.
3. **Refine a card into an executable issue** — `cp-software-spec --refine-card
   <ID>` promotes a backlog card to `2-todo/` with DoR, contracts and target files.
4. **Run the pipeline** — `cp-orchestrator` runs the crews in sequence with
   quality gates.
5. **Dispatch tasks** — `cp-agile --daemon` polls the backlog and dispatches
   ready tasks to the orchestrator.

## Decisions

- No persistent DB: the "state" is the filesystem (`.context/`, `outputs/`).
- The kanban is the source of truth for task flow; Trello is only a mirror.
