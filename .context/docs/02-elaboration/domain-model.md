# Domain Model — Core Product Skills

> Updated 2026-11-03 (RUP family).

## Status

- [x] Done (derived from the existing code)

## Core entities

There is no persistent domain model in the traditional sense — the "entities"
are the RUP concepts the skills encode and the files they exchange.

| Entity | Description | Where it lives |
|--------|-------------|----------------|
| **Skill** (`rup-*`) | Self-contained unit: `SKILL.md` + `scripts/run.py` + `references/` | `skills/rup-<name>/` |
| **Discipline** | One of the 8 RUP disciplines dispatched by the orchestrator | `DISCIPLINES` in `rup-orchestrator/scripts/run.py` |
| **Agent** (RUP role) | A CrewAI agent embedded in a skill (`AGENTS` dict) — 21 in total | each `run.py` |
| **Phase / Milestone** | Inception/LCO, Elaboration/LCA, Construction/IOC, Transition/PR | `PHASES`, `PHASE_MILESTONES` |
| **Artifact** | Markdown output of a discipline crew (`--output`) | wherever `--output` points |
| **Chained context** | Briefing + earlier artifacts passed to the next discipline in `--auto` | temp dir, via `--input` |
| **Sizing model** | JSON of actors, use cases, TCF/EF factors and h/UCP | `--sizing` file / tool input |
| **Kanban card** | Task `.md` with YAML frontmatter; the column is the folder | `.context/kanban/{column}/{ID}.md` |
| **ADR** | Architecture Decision Record | `.context/tracking/decisions.md` |

## Aggregates

- **Lifecycle** (root: `rup-orchestrator`) — phases, milestones, Work Orders,
  sizing and the ordered set of disciplines.
- **Discipline crew** (root: the discipline skill) — its agents and their
  sequential tasks; one artifact section per RUP artifact the agents own.

## Core use cases

1. **Govern an iteration** — `rup-orchestrator "<demand>" --phase P` produces
   SDP/Business Case/Risk List updates, sizing, Iteration Plan and Work Orders.
2. **Size the software** — `rup-orchestrator --estimate --sizing F` (no LLM), or
   the agent calls the `use_case_points_calculator` tool during governance.
3. **Run one discipline** — `rup-orchestrator "<briefing>" --discipline <key>`
   or the discipline's own `run.py`.
4. **Run the whole iteration** — `rup-orchestrator "<briefing>" --auto
   [--output F]`: 8 disciplines in order, each one building on the previous
   artifacts; stops at the first failure.

## Decisions

- No persistent DB: the "state" is the filesystem (`.context/`, `--output` files).
- The kanban is the source of truth for task flow; Trello is only a mirror.
