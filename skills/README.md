# rup — Rational Unified Process family

A family of skills implementing the **RUP (Rational Unified Process)** as a team
of roles that **the agent running the skill plays itself** (ADR-0012), strictly
grounded in *The Rational Unified Process:
An Introduction* (3rd ed.), Philippe Kruchten (Addison-Wesley / IBM Rational
Software).

The user interacts with `cp-orchestrator`, the front door: `--route
"<request>"` gives the agent the project state and every route, so the agent
picks and runs the right skill itself (discover, requirements, backlog, build,
debug, review, test audit) — the user never names a skill (ADR-0017). It also
governs the lifecycle and drives the 8 discipline skills. Together they cover the **9 RUP disciplines**
and **21 roles** (1 orchestrator + 20 specialists).

## Disciplines

| Skill | Discipline | Agents | Agent slugs |
|-------|------------|--------|-------------|
| `cp-orchestrator` | Project Management (governance) | 1 | `cp-orchestrator` |
| `cp-environment` | Environment | 1 | `process-engineer` |
| `cp-business-modeling` | Business Modeling | 2 | `business-process-analyst`, `business-designer` |
| `cp-requirements` | Requirements | 2 | `system-analyst`, `requirements-specifier` |
| `cp-analysis-design` | Analysis & Design | 5 | `software-architect`, `designer`, `user-interface-designer`, `database-designer`, `capsule-designer` |
| `cp-implementation` | Implementation | 2 | `system-integrator`, `implementer` |
| `cp-test` | Test (+ test-value audit: static audit, mutation, triage — ADR-0016) | 4 | `test-manager`, `test-analyst`, `test-designer`, `tester` |
| `cp-ccm` | Configuration & Change Management | 2 | `configuration-manager`, `change-control-manager` |
| `cp-deployment` | Deployment | 2 | `deployment-manager`, `technical-writer` |

## Execution skills (ADR-0013)

Six skills conduct the work (they replace the superpowers plugin) and keep its
state in `.context/`: cards, roadmap, generated board. 15 skills in total.

| Skill | Purpose | Commands |
|-------|---------|----------|
| `cp-context` | Detect, ask authorization, adopt the standard, import docs | `--status`, `--init --authorized-by`, `--import`, `--record-import` |
| `cp-discover` | Discovery conversation, recorded in Inception | packet (`"<idea>"`), `--record` |
| `cp-backlog` | Epics/stories/tasks, moves, roadmap, views | `--new`, `--show`, `--list`, `--move`, `--derive`, `--release-new`, `--iteration-new`, `--plan`, `--roadmap` |
| `cp-build` | Task/bug execution with TDD and test-value checks | `--start`, `--finish --delivery` |
| `cp-debug` | Bug card, root cause before fix | `--open`, `--diagnose` |
| `cp-review` | Review checklist and verdict | `<ID>`, `--record <ID> --doc` |

Every writing command needs the marker `.context/.rup-standard` (exit 5 without
it: ask the user, then `cp-context --init`). Cards: `EP/ST/TK/BUG-NNN`, one file
in `.context/kanban/<column>/`; criteria `ST-NNN/AC-n`; roadmap in
`.context/roadmap/`; generated `docs/06-roadmap.md` and `docs/06-board.md`.
Moves are declarations (`--move ID COLUMN --reason`); the skills never run git or
the project's tests, except `cp-test --mutate` (mutation testing in disposable
copies, with the suite command the agent wrote in `.context/tests/profile.json`).

## Lifecycle

```
Inception --> Elaboration --> Construction --> Transition
   LCO            LCA              IOC             PR
```

## Structure

```
skills/
├── README.md                 # this file
├── _shared/                  # helpers, not a skill
│   ├── rup.py                # phases, ordered disciplines, exit codes
│   ├── discipline.py         # work packet + --record engine
│   ├── context.py            # .context/ persistence + authorization marker
│   ├── consent.py            # --status/--init/--import, pointer note
│   ├── frontmatter.py        # card frontmatter parser/writer
│   ├── cards.py              # cards, moves, roll-up, derivation
│   ├── roadmap.py            # releases, iterations, generated views
│   ├── testcheck*.py         # test-value checks of a delivery (Python ast, JS/TS patterns)
│   ├── testaudit.py          # static audit of a whole suite
│   ├── router.py             # front door: .context/ state + routes (--route)
│   └── mutation.py           # mutants, parallel resumable runner, report, triage
├── cp-orchestrator/         # front door (--route), governance, iteration protocol, UCP
│   ├── SKILL.md
│   ├── scripts/run.py
│   └── references/           # lifecycle.md, sizing-estimation.md
├── cp-environment/          # discipline 1
├── cp-business-modeling/    # discipline 2
├── cp-requirements/         # discipline 3
├── cp-analysis-design/      # discipline 4
├── cp-implementation/       # discipline 5
├── cp-test/                 # discipline 6
├── cp-ccm/                  # discipline 7
├── cp-deployment/           # discipline 8
└── cp-{context,discover,backlog,build,debug,review}/   # execution skills
```

Each discipline skill: `SKILL.md` (how the agent runs it) + `scripts/run.py`
(the discipline's roles, missions and artifacts **as data**, plus a call to the
shared engine) + `references/agents.md` (role → artifact mapping). Standard
library only.

## How it runs — the agent is the LLM

1. `python scripts/run.py "<briefing>" --phase P` → prints the **work packet**:
   roles (goal, perspective, mission), the exact artifacts to write, the briefing
   and the earlier artifacts already in `.context/` (governance + earlier
   disciplines of the phase). Read-only.
2. The agent writes ONE document: `# <Role>` + `## <Artifact>` per artifact.
3. `python scripts/run.py --record doc.md --phase P ["<briefing>"]` (or
   `--record -` for stdin) → checks every required `## <Artifact>` and writes
   `.context/docs/<NN-phase>/cp-<skill>.md` + a row in `.context/tracking/rup-log.md`.

## CLI contract

```bash
# any skill
python scripts/run.py "briefing" [--input F] [--phase P] [--context-dir D]   # work packet
python scripts/run.py --record doc.md [--phase P] ["briefing" | --input F]   # record

# the orchestrator adds
python scripts/run.py "briefing" --discipline requirements   # that discipline's packet
python scripts/run.py "briefing" --auto                      # iteration protocol, in order
python scripts/run.py --status [--phase P]                   # what is recorded / next step
python scripts/run.py --list
python scripts/run.py --sizing-template > sizing.json
python scripts/run.py --estimate --sizing sizing.json [--json]   # UCP, recorded in .context/
```

Exit codes: `0` success · `1` usage error / missing artifacts / invalid sizing
model / invalid card or document / rejected delivery · `4` `.context/` not
writable · `5` needs authorization (no `.rup-standard` marker).

`.context/` = `--context-dir`, else `$RUP_CONTEXT_DIR`, else the nearest
`.context/` up to the git root (ADR-0011). Curated docs are never overwritten —
generated artifacts are `cp-<skill>.md`.

## Software sizing (owned by the orchestrator)

The orchestrator produces **Software Sizing & Effort Estimation** — Function
Points (IFPUG/NESMA), **Use Case Points** (UAW/UUCW/UUCP/TCF/EF) and parametric
estimates (COCOMO II, SLOC/KLOC) — feeding the Measurement Plan and the
Iteration Plan. The UCP calculation is implemented deterministically in
`cp-orchestrator/scripts/run.py` (`compute_ucp`); the governance packet tells
the agent to build the sizing model and run `--estimate` instead of computing it.
Details and formulas: `cp-orchestrator/references/sizing-estimation.md`.

## Provenance

Generated from `~/Downloads/especificacao_agentes_rup.md`, which defines the 9
disciplines, the 20 agents (base RUP roles, missions and artifacts), the
4-phase lifecycle mapping (section 3) and the traceability matrix (section 5).
