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
| **Role** (RUP worker) | Goal, perspective, mission and owned artifacts — data in the skill's `SPEC`; 21 in total | each `run.py` |
| **Host agent** | The agent running the skill (Claude Code, Hermes) — plays the roles, i.e. is the LLM | outside this repo |
| **Phase / Milestone** | Inception/LCO, Elaboration/LCA, Construction/IOC, Transition/PR | `_shared/rup.py`, `_shared/context.py` |
| **Work packet** | Markdown the skill prints for the host: roles, required artifacts, briefing, earlier artifacts | stdout of `run.py` |
| **Artifact document** | The host's document, `## <Artifact>` per required artifact, validated by `--record` | `.context/docs/<NN-phase>/rup-<skill>.md` |
| **Sizing model** | JSON of actors, use cases, TCF/EF factors and h/UCP | `--sizing` file / tool input |
| **Kanban card** | Task `.md` with YAML frontmatter; the column is the folder | `.context/kanban/{column}/{ID}.md` |
| **ADR** | Architecture Decision Record | `.context/tracking/decisions.md` |

## Aggregates

- **Lifecycle** (root: `rup-orchestrator`) — phases, milestones, Work Orders,
  sizing and the ordered set of disciplines.
- **Discipline** (root: the discipline skill) — its roles, in order, and the
  artifacts each owns; one `## ` section per artifact in the recorded document.

## Core use cases

1. **Govern an iteration** — governance packet → the host writes Phase
   Classification, SDP, Business Case, Risk List, Sizing, Iteration Plan, Work
   Orders, Acceptance Criteria & Measurement Plan → `--record`.
2. **Size the software** — the host fills a sizing model and runs
   `rup-orchestrator --estimate --sizing F` (recorded as `rup-orchestrator-sizing.md`).
3. **Run one discipline** — its packet (`--discipline <key>` or its own `run.py`)
   → document → the discipline's `--record`.
4. **Run the whole iteration** — `rup-orchestrator "<briefing>" --auto` prints the
   protocol; the host runs governance + 8 disciplines in order, each packet
   embedding what the earlier steps recorded; `--status` resumes.

## Decisions

- No persistent DB: the "state" is the filesystem (`.context/`).
- The kanban is the source of truth for task flow; Trello is only a mirror.
