# Domain Model — Core Product Skills

> Updated 2026-11-03 (RUP family).

## Status

- [x] Done (derived from the existing code)

## Core entities

There is no persistent domain model in the traditional sense — the "entities"
are the RUP concepts the skills encode and the files they exchange.

| Entity | Description | Where it lives |
|--------|-------------|----------------|
| **Skill** (`cp-*`) | Self-contained unit: `SKILL.md` + `scripts/run.py` + `references/` | `skills/cp-<name>/` |
| **Discipline** | One of the 8 RUP disciplines dispatched by the orchestrator | `DISCIPLINES` in `cp-orchestrator/scripts/run.py` |
| **Role** (RUP worker) | Goal, perspective, mission and owned artifacts — data in the skill's `SPEC`; 21 in total | each `run.py` |
| **Host agent** | The agent running the skill (Claude Code, Hermes) — plays the roles, i.e. is the LLM | outside this repo |
| **Phase / Milestone** | Inception/LCO, Elaboration/LCA, Construction/IOC, Transition/PR | `_shared/rup.py`, `_shared/context.py` |
| **Work packet** | Markdown the skill prints for the host: roles, required artifacts, briefing, earlier artifacts | stdout of `run.py` |
| **Artifact document** | The host's document, `## <Artifact>` per required artifact, validated by `--record` | `.context/docs/<NN-phase>/cp-<skill>.md` |
| **Sizing model** | JSON of actors, use cases, TCF/EF factors and h/UCP | `--sizing` file / tool input |
| **Kanban card** | Epic/story/task/bug `.md` with frontmatter and fixed sections; the column is the folder | `.context/kanban/{column}/{ID}.md` |
| **Acceptance criterion** | `ST-NNN/AC-n` in a story; tasks cover them, tests reference them | story card |
| **Release / Iteration** | Roadmap files; an iteration has a RUP phase and holds epics | `.context/roadmap/` |
| **Authorization marker** | Proves the user approved the RUP standard in this `.context/` | `.context/.rup-standard` |
| **ADR** | Architecture Decision Record | `.context/tracking/decisions.md` |

## Aggregates

- **Lifecycle** (root: `cp-orchestrator`) — phases, milestones, Work Orders,
  sizing and the ordered set of disciplines.
- **Discipline** (root: the discipline skill) — its roles, in order, and the
  artifacts each owns; one `## ` section per artifact in the recorded document.

## Core use cases

1. **Govern an iteration** — governance packet → the host writes Phase
   Classification, SDP, Business Case, Risk List, Sizing, Iteration Plan, Work
   Orders, Acceptance Criteria & Measurement Plan → `--record`.
2. **Size the software** — the host fills a sizing model and runs
   `cp-orchestrator --estimate --sizing F` (recorded as `cp-orchestrator-sizing.md`).
3. **Run one discipline** — its packet (`--discipline <key>` or its own `run.py`)
   → document → the discipline's `--record`.
4. **Run the whole iteration** — `cp-orchestrator "<briefing>" --auto` prints the
   protocol; the host runs governance + 8 disciplines in order, each packet
   embedding what the earlier steps recorded; `--status` resumes.

5. **Adopt the standard** — `cp-context --status` → ask the user → `--init`.
6. **Plan** — `cp-discover` → requirements → `cp-backlog` cards, releases,
   iterations, `--plan`.
7. **Deliver a task** — `cp-build --start` → test first → `--finish` (test
   checks) → `cp-review` verdict → `--move` to `7-done`; bugs via `cp-debug`.

## Decisions

- No persistent DB: the "state" is the filesystem (`.context/`).
- The kanban is the source of truth for task flow; Trello is only a mirror.
