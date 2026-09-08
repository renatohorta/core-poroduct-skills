---
name: cp-orchestrator
description: "Software Factory Orchestrator — coordinates the entire development pipeline by running specialized crews in sequence, managing artifacts between phases and deciding advance/rollback based on quality gates. Use when the user says 'run full pipeline', 'do software factory', 'deliver product', 'coordinate development', 'manage project'."
---

# cp-orchestrator — Software Factory Orchestrator

Central orchestrator of the NEXUS pipeline. Coordinates the execution of all specialized crews (`cp-*`) in sequence, manages the handoff of artifacts between phases, applies quality gates and decides advance/rollback.

## Full Pipeline (9 phases)

```
[Requirements] ──► [Architecture] ──► [Implementation] ──► [Testing] ──► [Security] ──► [DevOps] ──► [Documentation] ──► [Quality] ──► [Delivery]
      │                │                  │               │             │             │              │                │              │
  cp-requirements   cp-architecture    cp-implementation   cp-testing   cp-security  cp-devops   cp-software-spec  cp-quality   Delivery
      │                │                  │               │             │             │              │                │              │
  [Quality Gate]  [Quality Gate]    [Quality Gate]   [Quality Gate] [Quality Gate] [Quality Gate] [Quality Gate] [Quality Gate]  [Delivery]
```

## All triggerable cp-* skills

The orchestrator is the **single entry point** for ALL `cp-*` skills. Besides the 8
pipeline phases, it triggers the 6 complementary skills via dedicated modes:

| Mode | Skill | What it does |
|------|-------|--------------|
| `bugfix` | `cp-bug-fix` | Fixes bugs (Developer → QA → Evidence Collector, max. 3 retries) |
| `competitive` | `cp-competitive-analysis` | Competitive intelligence (market, competitors, pricing, strategy) |
| `full-dev` | **native** (merge of `cp-full-dev`) | Full NEXUS pipeline (Discovery → ... → Operate), now embedded in the orchestrator |
| `goal-loop` | `cp-goal-loop` | Autonomous trial-and-correction loop until success is reached |
| `maintenance` | `cp-maintenance` | Maintenance/evolution (bug-fix, refactor, improvement, full) |
| `agile` | `cp-agile` | Execution pipeline: monitors backlog, dispatches tasks and manages bidirectional feedback (questions, blockers, resume) |
| `software-spec` | `cp-software-spec` | Initializes documentation: centralizes context in `.context/` (single source of truth, RUP 4 phases) and creates CLAUDE.md/AGENT.md pointers |

> **Note:** `cp-full-dev` was **merged** into the orchestrator. The NEXUS pipeline (7 phases,
> 39 agents) now runs natively via `NexusExecutor` — it no longer depends on the
> `cp-full-dev` skill (which was removed). The `full-dev` mode runs NEXUS in memory, with
> automatic mode detection (full/sprint/micro) and per-phase quality gates.

Each skill is triggered respecting its CLI interface (`invoke` metadata in `CREWS`):
- `briefing_arg`: `positional` (positional arg), `goal` (`--goal`, e.g. goal-loop),
  `input` (`--input`, pipeline phases), `daemon` (no positional briefing —
  builds `--daemon`, e.g. agile), `dir` (builds `--init --dir <cwd>`, e.g.
  software-spec) or `inspect` (builds `--inspect <cwd>`, e.g. documentation)

> ⚠️ Do NOT assume every skill accepts `--output` nor that the briefing enters as a
> positional — each skill has its own CLI contract. See
> `references/skills-cli-inventory.md` for the complete per-skill inventory and the
> verification snippet. Pitfalls: `cp-goal-loop` only receives briefing via `--goal`;
> `cp-bug-fix`/`cp-goal-loop`/`cp-agile` reject `--output`; `cp-agile` has no
> positional argument (only `--daemon`/`--question`/`--blocker`/`--resume`);
> `cp-software-spec` has no positional (only `--init`/`--inspect`/`--refine-card`/`--dir`/`--dry-run`).

## Documentation rule in `.context/`

Every `cp-*` skill documents its artifacts in the **`.context/`** structure (the
project's single source of truth). The `cp-software-spec` creates the structure; the orchestrator
automatically writes each phase's artifact to the correct discipline file:

| Crew | File in `.context/docs/` |
|------|--------------------------|
| requirements, competitive-analysis | `01-inception/requirements.md` |
| architecture, implementation, maintenance | `02-elaboration/architecture.md` |
| security | `01-inception/requirements.md` |
| testing, quality, bug-fix | `04-transition/test-strategy.md` |
| devops, goal-loop | `04-transition/devops-infra.md` |
| documentation | `03-construction/api-contracts.md` |
| agile | `06-kanban.md` |

`cp-agile` also generates `.context/docs/06-kanban.md` with the kanban state
via `--doc`.

### How to add a new skill to the orchestrator

To connect a new `cp-*` skill to the flow, edit `scripts/run.py` in 4 places:
1. **`SKILL_PATHS`** — add `"<key>": SKILLS_DIR / "cp-<name>" / "scripts" / "run.py"`
2. **`CREWS`** — add the crew with `name`, `skill`, `agents`, `inputs`, `outputs`,
   `quality_gate`, `cli_args` and the `invoke` metadata (the `briefing_arg` MUST reflect
   how the skill actually receives the briefing — test with `_build_cli_args`).
3. **`MODOS`** — add the mode with `crews: ["<key>"]`.
4. **`_build_cli_args`** — if the skill uses a new `briefing_arg` (e.g.: `daemon`),
   add the corresponding branch.

Validate with: `python run.py "<briefing>" --mode <mode> --dry-run` (plan) and
`python run.py "<briefing>" --mode <mode> --auto` (execution). If the skill does not accept
`--output`, the `invoke.output=False` metadata is MANDATORY — without it the skill's
argparse rejects the flag and the phase breaks.

Examples:
```bash
python run.py "the /login endpoint returns 500" --mode bugfix --auto
python run.py "clinics SaaS; competitors: Doctoralia" --mode competitive --auto
python run.py "scheduling system" --mode full-dev --auto
python run.py "deploy to staging working" --mode goal-loop --auto
python run.py "refactor payments module" --mode maintenance --auto
```

## Agents

| Agent | Role |
|-------|------|
| **Pipeline Orchestrator** | Coordinates sequential/parallel execution of the crews. Software orchestra conductor who knows each instrument and when to play it. |
| **Artifact Manager** | Ensures one crew's outputs become the next crew's inputs, versions artifacts. Software librarian who organizes and versions every artifact produced. |
| **Decision Maker** | Decides to advance, pause, or roll back based on the quality gates. Experienced project manager who knows when to push and when to pull back. |
| **Progress Reporter** | Generates pipeline status reports, dashboards, executive summaries. PM who turns technical progress into reports stakeholders understand. |

## Operation Modes

The orchestrator operates in **two modes**:

### 🧪 Simulation (default)

Uses CrewAI to plan, simulate and document the pipeline. Ideal for:
- Planning before executing
- Presentation to stakeholders
- Estimating effort and risks

### 🚀 Auto (--auto)

Runs the real crews in sequence, passing artifacts between phases and applying quality gates automatically. Ideal for:
- Real pipeline execution from start to finish
- Continuous integration / deploy pipeline
- Use as the "factory manager" — a single command

**How auto mode works:**

```
1. Receives the briefing
2. Runs cp-requirements → saves requirements.md
3. Passes requirements.md as input to cp-architecture
4. Runs cp-architecture → saves architecture.md
5. Passes architecture.md as input to cp-implementation
6. ... continues until the last phase
7. If a quality gate FAILs, the pipeline stops and reports
8. Generates a final report with dashboard and metrics
```

## Quality Gates

Each phase has a quality gate that evaluates:

- **PASS** → Advances to the next phase
- **WARN** → Advances with documented caveats
- **FAIL** → Pipeline stops with fix recommendations

In `--auto` mode, the quality gate is checked automatically by analyzing each skill's output. If FAIL, the pipeline stops and you can fix and resume with `--start-phase`.

## Usage

```bash
# Simulation (planning with CrewAI)
python .hermes/skills/cp-orchestrator/scripts/run.py "scheduling system for clinics"

# Automatic execution (runs the real crews)
python .hermes/skills/cp-orchestrator/scripts/run.py "scheduling system" --auto

# Automatic sprint mode
python .hermes/skills/cp-orchestrator/scripts/run.py "PDF report feature" --mode sprint --auto

# Automatic bug fix
python .hermes/skills/cp-orchestrator/scripts/run.py "fix login error" --mode micro --auto

# Security audit
python .hermes/skills/cp-orchestrator/scripts/run.py "finance app" --mode security-audit --auto

# Documentation
python .hermes/skills/cp-orchestrator/scripts/run.py "payments API" --mode documentation --auto

# With a file briefing
python .hermes/skills/cp-orchestrator/scripts/run.py --input briefing.txt --auto

# Start from a specific phase (after a fix)
python .hermes/skills/cp-orchestrator/scripts/run.py "inventory system" --start-phase implementation --auto

# Just view the plan
python .hermes/skills/cp-orchestrator/scripts/run.py "scheduling system" --dry-run

# Save artifacts to a specific directory
python .hermes/skills/cp-orchestrator/scripts/run.py "delivery app" --output ./pipeline --auto
```

## Example

```bash
python .hermes/skills/cp-orchestrator/scripts/run.py \
  "I need a system for an aesthetics clinic where the receptionist schedules clients, \
   the aesthetician sees her daily schedule, and the clinic owner wants revenue reports. \
   It also needs to send a WhatsApp reminder automatically." \
  --mode full --output ./pipeline-report.md
```

## Single Entry Point (Factory Manager)

The `cp-orchestrator` is the **software factory manager** — direct all requests to it. It analyzes the briefing, chooses the mode, plans the phases, sets quality gates and generates the report.

### Simulation Mode (default)

By default the orchestrator **simulates** the execution — documents what each phase would produce, without calling the other skills. Useful for planning, stakeholder presentations and effort/risk estimation.

### `--auto` Mode (real executor)

The `--auto` mode runs the real crews in sequence, passing artifacts between phases and applying quality gates automatically:
1. Plans the pipeline
2. Calls `cp-requirements` → receives requirements.md
3. Calls `cp-architecture --input requirements.md` → receives architecture.md
4. Calls `cp-implementation --input architecture.md` → receives code
5. ... until the final delivery
6. Generates a complete report

Each phase only advances if the quality gate passes. If it fails, it pauses and documents what needs to be fixed (resume with `--start-phase`). The `--auto` mode also triggers the complementary skills (`bugfix`, `competitive`, `full-dev`, `goal-loop`, `maintenance`).

## Script

The `scripts/run.py` script is self-contained — all 4 agents are embedded in the Python code itself. It lists the available crews, simulates the pipeline execution (default mode) and runs the real crews in sequence (`--auto` mode), triggering all `cp-*` skills via subprocess. It does not depend on an external agents directory.

## Roadmap and inbox maintenance (crewbotics-back)

Before reporting "what's missing" or updating `.hermes/roadmap/tasks.md`, ALWAYS cross-check the
roadmap/inbox state against the real code (models, endpoints, tests) — the roadmap
often marks as pending things already implemented (and sometimes in the wrong app).
See `references/roadmap-inbox-manutencao.md` for the complete procedure: real-state
verification, inbox→processed convention (features `[Concluído]` and bugs `[Corrigido]`
moved via `git mv`), frontend in another repo, and the pitfall of writing tools masking
example placeholders.

## Windows: intermittent bash relay

On this Windows host, `terminal`/`write_file` sometimes fail with
`execvpe(/bin/bash) failed: No such file or directory` (intermittent WSL relay).
When this happens, use `execute_code` with pure Python (subprocess/open) — it does not
go through the relay. See `references/windows-wsl-bash-relay-workaround.md`.

## Pipeline execution (crewbotics-back) — real pitfalls

When running the development pipeline (running tests, committing, validating), see
`references/dev-pipeline-execucao.md` for durable lessons: tests run with
`uv run pytest` (there is no own `.venv`), tests that touch the database fail without
`.env`/Postgres (pre-existing, not your change), ALWAYS check
`git status --short` before committing (a commit can come out incomplete if not all
files were staged), close PIL images before deleting a tempdir on Windows,
and use `True`/`False` (not `true`/`false`) in Python parameter dicts.

## Skill design: auto-detect the mode, don't rely on the LLM remembering a flag

When adding an alternative rendering mode to a skill (e.g.: `card_mode` to
toggle between a card executor and a brand renderer), do NOT rely on an optional flag
that the LLM needs to remember to set — the LLM calls the skill via function calling and decides
the parameters on its own, so a blind `default=False` flag makes the new mode
never get triggered. The correct mode should be DETECTED automatically from the
prompt (e.g.: "date + title" pattern in a list → release cards). See
`references/skill-design-auto-detect.md` for the complete rule and the detection
heuristic.

## Debug: "code correct locally but doesn't work in the app"

Before debugging a skill that seems to have no effect on the web app, confirm FROM WHICH
directory the backend process (port 8000) is running — it may be starting from an
old repo CLONE (e.g.: `PycharmProjects\crewbotics-back`) that doesn't have the feature,
while the real work lives in another clone (e.g.: `Documents\Professional\...`).
Check the listener's CommandLine via PowerShell and compare the skill file between
the clones. See `references/debug-backend-clone-errado.md` for the step-by-step.

## Resume/portfolio carousel (new use case, not covered)

`instagram_carousel_skill.py` today covers: (a) release cards with date (automatic
detection) and (b) brand narrative carousel. It does NOT cover well "carousel of MY
resume/portfolio + real photo" — it falls into the generic brand path, ignores the photo and
reuses the `constellation` fallback template (layout identical to the previous case, which
confuses the user). For this case a dedicated executor is needed: resume →
slides + photo on the cover. When debugging "generated the same layout as the previous
request", check whether the skill actually consumed the new input or fell into the fallback.
