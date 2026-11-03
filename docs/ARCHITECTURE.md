# Architecture

The skills under `skills/` implement the **Rational Unified Process** (Kruchten,
3rd ed.): **9 disciplines, 21 roles** (1 orchestrator + 20 specialists).

**The agent running a skill is the LLM** (ADR-0012). The skills are deterministic,
standard-library scripts: they compile a *work packet* for the agent and record
the agent's document into the project's `.context/` (mandatory, ADR-0011). There
is no model call, API key, proxy or CrewAI in the repository.

> History: the legacy Software Factory family (removed in ADR-0010) also used the
> `cp-` prefix; the current `cp-*` skills are the RUP skills, renamed from `rup-*`
> (ADR-0014). The CrewAI execution was replaced by the host-LLM model (ADR-0012).

Besides the 9 document skills there are **6 execution skills** (ADR-0013) that
conduct the work: `cp-context`, `cp-discover`, `cp-backlog`, `cp-build`,
`cp-debug`, `cp-review` — 15 skills in total.

```
            ┌──────────────── host agent (Claude Code / Hermes) = the LLM ────────────────┐
            │                                                                             │
   1. run.py "<briefing>" --phase P            3. run.py --record doc.md --phase P
            │                                         │
            ▼                                         ▼
   ┌──────────────────────────┐            ┌──────────────────────────────┐
   │ WORK PACKET (read-only)  │  2. agent  │ validate "## <Artifact>"     │
   │ roles · missions         │  writes    │ write .context/docs/<NN>/    │
   │ required artifacts       │ ─────────► │       cp-<skill>.md         │
   │ briefing                 │  ONE doc   │ log   .context/tracking/     │
   │ earlier .context/ arts.  │            │       rup-log.md             │
   └──────────────────────────┘            └──────────────────────────────┘
```

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| Registry | `skills/_shared/rup.py` | Phases, the ordered disciplines, exit codes, console UTF-8 |
| Engine | `skills/_shared/discipline.py` | Work packet rendering, `--record` validation, CLI shared by all skills |
| Context | `skills/_shared/context.py` | `.context/` resolution, phase layout, provenance, log, writability, **authorization marker gate** |
| Consent | `skills/_shared/consent.py` | `--status` / `--init` / import, pointer note in `CLAUDE.md`/`AGENT.md` |
| Cards | `skills/_shared/{frontmatter,cards}.py` | Card parser/writer, IDs, criteria, moves, History, roll-up, derivation |
| Roadmap | `skills/_shared/roadmap.py` | Releases, iterations, generated `06-roadmap.md` / `06-board.md` |
| Test checks | `skills/_shared/testcheck*.py` | Value checks of the tests in a delivery (Python `ast`, JS/TS patterns) |
| Disciplines | `skills/cp-<discipline>/scripts/run.py` | The discipline's roles, missions and artifacts **as data** (`SPEC`) + `discipline.main()` |
| Orchestrator | `skills/cp-orchestrator/scripts/run.py` | Governance packet, `--discipline` (delegates to the skill), `--auto` protocol, `--status`, UCP `--estimate` |
| Execution skills | `skills/rup-{context,discover,backlog,build,debug,review}/` | Conduct the work: authorization, discovery, cards and roadmap, TDD delivery, bugs, review |
| Installer | `scripts/install.sh` | Copies every `skills/*/SKILL.md` dir + `_shared` to Hermes and Claude |

## Skill anatomy

`SKILL.md` (frontmatter + **how the agent runs it**: packet → document →
record) + `scripts/run.py` + `references/`. Each `run.py` finds `_shared/` next
to the skill directory (repository, Claude Code) or one level up (Hermes, which
installs skills under a category).

CLI: `run.py "<briefing>" [--input F] [--phase P] [--context-dir D]` (packet) and
`run.py --record FILE|- [--phase P] ["<briefing>" | --input F]` (record).
Exit codes: 0 ok · 1 usage / invalid document / rejected delivery · 4 `.context/`
not writable · 5 needs authorization.

## Chaining and the iteration

A discipline's packet embeds, from `.context/docs/<NN-phase>/`, the governance
artifact and the artifacts of the disciplines **before** it in RUP order
(environment → business modeling → requirements → analysis & design →
implementation → test → CCM → deployment), each capped at 12 000 chars and
without its provenance header. The governance packet embeds every discipline
artifact of the phase. So doing the steps in order makes each one build on the
previous ones.

`cp-orchestrator "<briefing>" --auto` prints that protocol (step 0 governance +
8 disciplines, with exact commands); `--status` lists what is recorded per step
and the next pending one. `--discipline <key>` prints that discipline's packet by
running its skill (subprocess, ADR-0004) with an explicit `--context-dir`.

## Artifacts in `.context/` (mandatory — ADR-0011)

| What | Where |
|------|-------|
| Discipline artifact | `.context/docs/<NN-phase>/cp-<discipline>.md` |
| Governance | `.context/docs/<NN-phase>/cp-orchestrator.md` |
| UCP estimate | `.context/docs/<NN-phase>/cp-orchestrator-sizing.md` |
| Log | `.context/tracking/rup-log.md` (one line per artifact) |

Resolution: `--context-dir` > `$RUP_CONTEXT_DIR` > nearest `.context/` walking up
from cwd, stopping at the git root > `<git root or cwd>/.context`. Each file has a
provenance frontmatter and is regenerated per run; curated docs are never touched.

## Authorization gate (ADR-0013)

Every writing command checks `.context/.rup-standard` (in `_shared/context.py`).
Without it nothing is written and the skill exits **5**, printing what was
found, what would change and "ask the user; on approval run `cp-context
--init`". `--init` only adds missing folders/skeletons, the marker and a pointer
block in `CLAUDE.md`/`AGENT.md`; it never overwrites or deletes. Read-only
packets work without the marker (with a warning).

## Cards, roadmap and views

```
.context/kanban/<column>/<ID>.md   EP/ST/TK/BUG-NNN, frontmatter + fixed sections, ## History last
.context/roadmap/R<n>.md           releases;  R<n>-I<m>.md  iterations (RUP phase)
.context/docs/06-roadmap.md        generated by cp-backlog, never hand-edited
.context/docs/06-board.md          generated: board by column
```

`cp-backlog --move ID COLUMN --reason R` moves a card on declaration (any move is
legal; skipped columns only warn in History), logs it and regenerates the
views; stories and epics roll up automatically. `cp-build --finish` checks the
tests listed in the delivery (exist, tied to a criterion, non-trivial, red
evidence) before the card goes to `4-review`; `cp-review` records the verdict.
The skills never run git or the project's tests.

## Software sizing

`compute_ucp` (validated by `ucp_from_model`) runs on `--estimate`. The
governance packet instructs the agent to build the sizing model
(`--sizing-template`) and run `--estimate` — never to compute UCP itself. FPA and
COCOMO II are the agent's estimates, with inputs and arithmetic shown.

## Portability

- **Zero hardcoded OS/machine paths**, **zero fixed personal values**
- No runtime dependency: Python 3.10+ standard library
