---
name: cp-doc-initializer
description: "Documentation Initializer — centralizes the project context in .context/ (single source of truth), creates the CLAUDE.md and AGENT.md bridge files at the root, ingests vision.md and generates the complete documentation structure covering all engineering disciplines (requirements, architecture, security/LGPD, quality/QA, devops/operations, inbox, tracking and the pipeline kanban). Use when the user says 'initialize documentation', 'start project', 'docs setup', 'create context structure', 'initialize repo', 'prepare project documentation'."
---

# cp-doc-initializer — Documentation Initializer

Centralizes the project context in **`.context/`** as a single source of truth,
eliminating the pollution of directories such as `.hermes/` or `.claude/`. Creates
bridge files at the root (`CLAUDE.md` and `AGENT.md`) that instruct any agent to use
exclusively `.context/`.

## Analogy

Imagine a **documentation architect** who organizes the house before the construction:

```
[Repo root]
   ├── CLAUDE.md  ──► "use .context/ as source of truth"
   ├── AGENT.md   ──► "use .context/ as source of truth"
   └── .context/  ──► (single source of truth)
        ├── docs/          (engineering disciplines)
        ├── inbox/         (initiatives, tasks, bugs, tech debt)
        ├── tracking/      (progress tracking)
        └── kanban/        (execution pipeline — cp-agile)
```

## Usage

```
/load skill cp-doc-initializer
initialize project documentation
```

Or:

```
initialize the documentation of this repository
```

## Structure generated in `.context/`

```
.context/
├── README.md                 # Index of the source of truth
├── docs/
│   ├── 00-vision.md          # Product vision + Initiatives (epics)
│   ├── 01-requirements.md    # Requirements (cp-requirements)
│   ├── 02-architecture.md    # Architecture (cp-architecture)
│   ├── 03-security-lgpd.md   # Security/LGPD (cp-security)
│   ├── 04-quality-qa.md     # Quality/QA (cp-quality, cp-testing)
│   ├── 05-devops-operations.md # DevOps/Operations (cp-devops)
│   └── 06-kanban.md          # Kanban/pipeline (cp-agile)
├── inbox/
│   ├── initiatives/          # Product initiatives (epics) — raw entry
│   ├── tasks/                # Tasks
│   ├── bugs/                 # Bugs
│   └── tech-debt/            # Technical debt
├── tracking/
│   ├── progress.md           # Overall project progress
│   └── decisions.md          # Decision record (ADRs)
└── kanban/                   # Execution pipeline (cp-agile)
    ├── README.md             # Columns, task format, commands
    ├── 1-backlog/            # Entry; the daemon scans for `status: ready`
    ├── 2-todo/
    ├── 3-doing/
    ├── 4-review/
    ├── 5-testing/
    ├── 6-staging/
    ├── 7-done/
    └── blocked/              # Questions and blockers awaiting answer
```

The kanban is born **at initialization**, not on the first run of `cp-agile`: the
pipeline needs a queue from day 1, and `.context/docs/06-kanban.md` references
`.context/kanban/`. The columns are created with `.gitkeep` because git does not
version empty directories. The constants mirror `KANBAN_COLUMNS`/`BLOCKED_DIR`
of `cp-agile/scripts/run.py` — changing one requires changing the other.

`inbox/` is raw entry (draft); after triage, the item becomes a task in
`kanban/1-backlog/`.

**Initiatives (epics)** have no separate file in `tracking/`: the aggregated view
of initiatives and their status is part of `docs/00-vision.md`. Each initiative
aggregates multiple kanban cards and the content of each individual card
(task, bug, technical debt) lives in the card itself inside `kanban/`.

## Bridge files at the root

- **`CLAUDE.md`** — instructs Claude Code to use `.context/` as source of truth.
- **`AGENT.md`** — instructs Hermes Agent (and other agents) to use `.context/`.

Both point to `.context/README.md` and forbid the creation of `.hermes/`/`.claude/`.

## Initialization flow

1. **README + pointers** — creates `.context/README.md`, `CLAUDE.md` and `AGENT.md` at the root (overwrites if they already exist, they are infrastructure).
2. **Disciplinary docs/** — creates `docs/00-vision.md` to `docs/06-kanban.md` **only if they do not exist**. Content already populated by skills or manual editing is preserved intact. `00-vision.md` uses its own `VISION_TEMPLATE`, with the `## Initiatives (Epics)` section.
3. **inbox/ + tracking/ + kanban/** — creates the folders and infrastructure READMEs (overwrite).
4. **Tracking → kanban migration** — if `tracking/tasks.md`, `tracking/bugs.md` or `tracking/tech-debt.md` exist, extracts each content section and injects it into the corresponding kanban card (`kanban/{column}/{ID}.md`). The tracking files are moved to `tracking/_backup_pre_migration/`. Idempotent: cards already with `## Tracking content` are ignored.
5. **`vision.md` ingestion** — if it exists at the root, moves it to `.context/docs/00-vision.md`.
6. **Gap report** — presents an executive summary and clarifying questions segmented by discipline to resolve doubts before implementation.

### Idempotency rules

| Target | Overwrites? | Reason |
|------|-------------|--------|
| `docs/*.md` | **No** | Content may already be populated |
| `README.md`, `CLAUDE.md`, `AGENT.md` | Yes | Infrastructure, no customization |
| `inbox/*/README.md` | Yes | Standardized template |
| `tracking/progress.md`, `tracking/decisions.md` | Yes | Standardized template |
| `kanban/README.md`, `.gitkeep` | Yes | Infrastructure |
| Existing kanban cards | **No** | `migrate_tracking_to_kanban()` skips if it already has `## Tracking content` |

### Canonical tracking structure

`tracking/` contains only:
- `progress.md` — overall project progress (managed by the orchestrator)
- `decisions.md` — ADR record

Individual tasks (bug, technical debt, feature task) have **full content inside the kanban card** (`kanban/{column}/{ID}.md`), not in separate tracking files. Initiatives/epics (aggregated view of multiple cards) live in `docs/00-vision.md`.

## Script

```bash
# Initialize documentation (uses the current directory)
python .hermes/skills/cp-doc-initializer/scripts/run.py

# Initialize in a specific directory
python .hermes/skills/cp-doc-initializer/scripts/run.py --dir /path/to/project

# Dry run (shows what it would do, without creating)
python .hermes/skills/cp-doc-initializer/scripts/run.py --dry-run
```

## Integration with the orchestrator

`cp-doc-initializer` is triggered by the `cp-orchestrator` via the
`doc-initializer` mode:

```bash
python .hermes/skills/cp-orchestrator/scripts/run.py "initialize documentation" --mode doc-initializer --auto
```

## Global rule: every cp-* skill documents in `.context/`

Every `cp-*` skill (requirements, architecture, implementation, testing, security,
devops, documentation, quality, bug-fix, competitive-analysis, goal-loop,
maintenance, agile) must **document its artifacts in `.context/`** following
the structure above. The `cp-doc-initializer` guarantees the structure exists; the
other skills write their outputs in the corresponding files of `.context/docs/`.
