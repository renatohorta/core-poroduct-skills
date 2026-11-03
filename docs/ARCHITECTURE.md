# Architecture

The skills under `skills/` implement the **Rational Unified Process** (Kruchten,
3rd ed.): **9 disciplines, 21 roles** (1 orchestrator + 20 specialists).

**The agent running a skill is the LLM** (ADR-0012). The skills are deterministic,
standard-library scripts: they compile a *work packet* for the agent and record
the agent's document into the project's `.context/` (mandatory, ADR-0011). There
is no model call, API key, proxy or CrewAI in the repository.

> History: the `cp-*` family was removed (ADR-0010); the CrewAI execution was
> replaced by the host-LLM model (ADR-0012). Both are in the git history.

```
            ┌──────────────── host agent (Claude Code / Hermes) = the LLM ────────────────┐
            │                                                                             │
   1. run.py "<briefing>" --phase P            3. run.py --record doc.md --phase P
            │                                         │
            ▼                                         ▼
   ┌──────────────────────────┐            ┌──────────────────────────────┐
   │ WORK PACKET (read-only)  │  2. agent  │ validate "## <Artifact>"     │
   │ roles · missions         │  writes    │ write .context/docs/<NN>/    │
   │ required artifacts       │ ─────────► │       rup-<skill>.md         │
   │ briefing                 │  ONE doc   │ log   .context/tracking/     │
   │ earlier .context/ arts.  │            │       rup-log.md             │
   └──────────────────────────┘            └──────────────────────────────┘
```

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| Registry | `skills/_shared/rup.py` | Phases, the ordered disciplines, exit codes, console UTF-8 |
| Engine | `skills/_shared/discipline.py` | Work packet rendering, `--record` validation, CLI shared by all skills |
| Context | `skills/_shared/context.py` | `.context/` resolution, phase layout, provenance, log, writability |
| Disciplines | `skills/rup-<discipline>/scripts/run.py` | The discipline's roles, missions and artifacts **as data** (`SPEC`) + `discipline.main()` |
| Orchestrator | `skills/rup-orchestrator/scripts/run.py` | Governance packet, `--discipline` (delegates to the skill), `--auto` protocol, `--status`, UCP `--estimate` |
| Installer | `scripts/install.sh` | Copies every `skills/*/SKILL.md` dir + `_shared` to Hermes and Claude |

## Skill anatomy

`SKILL.md` (frontmatter + **how the agent runs it**: packet → document →
record) + `scripts/run.py` + `references/`. Each `run.py` finds `_shared/` next
to the skill directory (repository, Claude Code) or one level up (Hermes, which
installs skills under a category).

CLI: `run.py "<briefing>" [--input F] [--phase P] [--context-dir D]` (packet) and
`run.py --record FILE|- [--phase P] ["<briefing>" | --input F]` (record).
Exit codes: 0 ok · 1 usage / missing artifacts · 4 `.context/` not writable.

## Chaining and the iteration

A discipline's packet embeds, from `.context/docs/<NN-phase>/`, the governance
artifact and the artifacts of the disciplines **before** it in RUP order
(environment → business modeling → requirements → analysis & design →
implementation → test → CCM → deployment), each capped at 12 000 chars and
without its provenance header. The governance packet embeds every discipline
artifact of the phase. So doing the steps in order makes each one build on the
previous ones.

`rup-orchestrator "<briefing>" --auto` prints that protocol (step 0 governance +
8 disciplines, with exact commands); `--status` lists what is recorded per step
and the next pending one. `--discipline <key>` prints that discipline's packet by
running its skill (subprocess, ADR-0004) with an explicit `--context-dir`.

## Artifacts in `.context/` (mandatory — ADR-0011)

| What | Where |
|------|-------|
| Discipline artifact | `.context/docs/<NN-phase>/rup-<discipline>.md` |
| Governance | `.context/docs/<NN-phase>/rup-orchestrator.md` |
| UCP estimate | `.context/docs/<NN-phase>/rup-orchestrator-sizing.md` |
| Log | `.context/tracking/rup-log.md` (one line per artifact) |

Resolution: `--context-dir` > `$RUP_CONTEXT_DIR` > nearest `.context/` walking up
from cwd, stopping at the git root > `<git root or cwd>/.context`. Each file has a
provenance frontmatter and is regenerated per run; curated docs are never touched.

## Software sizing

`compute_ucp` (validated by `ucp_from_model`) runs on `--estimate`. The
governance packet instructs the agent to build the sizing model
(`--sizing-template`) and run `--estimate` — never to compute UCP itself. FPA and
COCOMO II are the agent's estimates, with inputs and arithmetic shown.

## Portability

- **Zero hardcoded OS/machine paths**, **zero fixed personal values**
- No runtime dependency: Python 3.10+ standard library
