# Core Product Skills

## What this is

Core Product Skills is a set of **15 skills** for **Claude Code** and the
**Hermes Agent**. Together they bring the **Rational Unified Process (RUP)** into
the agent. It covers the whole path of a piece of software, from the first idea
to a reviewed delivery:

- discovery;
- requirements;
- a backlog of cards and a roadmap;
- test-first development;
- debugging;
- review;
- the RUP documentation;
- an audit that measures whether the tests actually catch bugs.

**The agent you already use does the work** (ADR-0012). The skills never call a
model, need no API key and have no runtime dependency (Python standard library
only). Each skill hands the agent a *work packet*: the RUP roles, missions,
required artifacts and the context already recorded. The agent writes the
document, and the skill validates it and records it in the project's
`.context/` folder (ADR-0011). That folder is the single source of truth for
docs, cards, roadmap and decisions.

The RUP part is grounded in *The Rational Unified Process: An Introduction*
(3rd ed.) by Philippe Kruchten: 9 disciplines and 21 roles.

This repository is the **single source of truth** for the skills. Every change
is made here and propagated to the agents with `scripts/install.sh`.

### The skills

**Document skills.** They produce the RUP artifacts:

| Skill | Discipline | Roles |
|-------|------------|-------|
| `cp-orchestrator` | Front door (routing) + Project Management (governance) | 1 |
| `cp-environment` | Environment | 1 |
| `cp-business-modeling` | Business Modeling | 2 |
| `cp-requirements` | Requirements | 2 |
| `cp-analysis-design` | Analysis & Design | 5 |
| `cp-implementation` | Implementation | 2 |
| `cp-test` | Test + test-value audit (mutation) | 4 |
| `cp-ccm` | Configuration & Change Management | 2 |
| `cp-deployment` | Deployment | 2 |

**Execution skills.** They conduct the work and keep its state in `.context/`
(ADR-0013):

| Skill | Use it to |
|-------|-----------|
| `cp-context` | Check the project's `.context/`, ask the user, adopt the standard (`--init`), import existing docs |
| `cp-discover` | Talk before building: problem, users, goals, non-goals, anti-goals |
| `cp-backlog` | Create epics/stories/tasks, derive them from requirements, move cards, plan releases/iterations, generate the roadmap and board |
| `cp-build` | Implement a task test-first, then deliver it with tests checked for value |
| `cp-debug` | Open a bug card, pin it with a regression test, record the root cause before the fix |
| `cp-review` | Review a card in `4-review` and record `approved` / `changes requested` |

Full details are in [`skills/README.md`](skills/README.md) and in each skill's
`SKILL.md`. Architecture and operation are in [`.context/docs/`](.context/docs/).

> History: the legacy Software Factory family (removed in ADR-0010) also used the
> `cp-` prefix. The current `cp-*` skills are the RUP skills, renamed from `rup-*`
> (ADR-0014). The CrewAI execution was replaced by the host-LLM model (ADR-0012).

## Installation

### Prerequisites

- Claude Code (or the Hermes Agent)
- Python 3.10+ and git
- bash (on Windows, use **Git Bash**)

### Install

```bash
git clone https://github.com/renatohorta/core-poroduct-skills.git
cd core-poroduct-skills
bash scripts/install.sh --claude
```

The skills go to `~/.claude/skills/`. Open a new Claude Code session and type
`/cp-` to see them.

Other options:

```bash
bash scripts/install.sh                          # every skill, Hermes + Claude
bash scripts/install.sh --hermes                 # Hermes only
bash scripts/install.sh --skill cp-requirements  # one skill
bash scripts/install.sh --claude --dry-run       # show the plan, install nothing
```

Destinations, overrides and the runbook are in
[`.context/docs/04-transition/devops-infra.md`](.context/docs/04-transition/devops-infra.md).

### Update

```bash
cd core-poroduct-skills && git pull && bash scripts/install.sh --claude
```

Never edit the installed copy in `~/.claude/skills`, because every install wipes
it and writes it again. Improvements go through a PR to this repository.

### First use in a project

Every artifact lives in the project's `.context/` folder.

- **Authorization.** The first time, the agent asks for authorization before it
  creates or changes `.context/`; just approve. Without it, the skills write
  nothing (exit 5).
- **Existing documentation.** If the project already has documentation
  (`docs/`, `.specs/`, another `.context/`), nothing is deleted. The agent asks
  and can import what already exists.
- **Projects set up before the front door (ADR-0017).** Ask "set up this
  project's .context" again. This refreshes the note in `CLAUDE.md` and
  `AGENT.md` so that routing is automatic.
- **Version control.** Commit `.context/` together with the code.

## Usage

### Just ask

**You don't need to know any skill name.** Describe what you want in plain
words. The agent goes through the orchestrator (`cp-orchestrator --route`).
The orchestrator reads the project state, picks the right skill and follows the
flow on its own (ADR-0017):

| You say… | The agent does |
|---|---|
| "I want a login screen with Google" | discovery → requirements → backlog → build each task → review |
| "checkout is returning a 500 error" | opens a BUG, reproduces it, regression test, root cause, fix, review |
| "change the text of the pay button" | task straight into the backlog → build → review (no discovery) |
| "review TK-012" | reviews the card and records the verdict |
| "are our tests worth anything?" | static audit + mutation testing + cards for the gaps |
| "what now?" / "continue" | the next step the project state points to |
| "document the whole project the RUP way" | governance + the 8 disciplines, in order |

The agent stops to ask you only when it needs you:

- authorizing `.context/`;
- the discovery conversation;
- confirming the generated cards;
- a real ambiguity between two routes;
- something destructive or outward-facing (push, deploy).

### Calling a skill directly

Every skill still works on its own:

| Skill | What for |
|---|---|
| `cp-orchestrator` | Routing (`--route`), RUP documentation, estimation (Use Case Points), iteration plan |
| `cp-discover` | Before building something new: problem, users, goals, what is out |
| `cp-backlog` | Epics, stories and tasks; releases and iterations; moving cards (`1-backlog` → `7-done`) |
| `cp-build TK-001` | Implements test-first (red test first); tests like `assert True` are rejected |
| `cp-debug` | BUG → reproduction → regression test → root cause **before** the fix |
| `cp-review TK-001` | Reviews a card in `4-review`: `approved` or `changes requested` |
| `cp-test --audit` | "Do the tests catch bugs?": static audit and mutation testing. In one of our projects, 96% line coverage caught only 76% of the mutants |

### How a skill runs

```
agent ──► run.py "<briefing>" --phase P        ─► WORK PACKET (read-only)
                                                   roles · missions · required artifacts
                                                   briefing · earlier .context/ artifacts
agent writes ONE document: "# <Role>" + "## <Artifact>" for each required artifact
agent ──► run.py --record doc.md --phase P     ─► validates every "## <Artifact>"
                                                   writes .context/docs/<NN-phase>/cp-<skill>.md
                                                   logs   .context/tracking/rup-log.md
```

- **Front door.** `cp-orchestrator --route "<request>"` reads the state of
  `.context/`: authorization, discovery, requirements, board, open bugs. It
  suggests the next step and lists every route with its command. The agent
  classifies the request and runs the chain itself.
- **Chaining.** A discipline's packet embeds the governance artifact and the
  artifacts of the earlier disciplines in the same phase, so each discipline
  builds on the previous ones.
- **Whole iteration.** `cp-orchestrator "<briefing>" --auto` prints the
  protocol: governance and the 8 disciplines, in order. `--status` shows what is
  recorded and the next pending step.
- **Sizing.** Use Case Points are computed by code (`--estimate`), never by the
  model.
- **Cards and views.** `cp-backlog` keeps cards in
  `.context/kanban/<column>/<ID>.md` and the roadmap in `.context/roadmap/`. It
  generates `docs/06-roadmap.md` and `docs/06-board.md`. `cp-build`, `cp-debug`
  and `cp-review` move a task from `3-doing` through review.
- **Test-value audit.** `cp-test --audit` prints the A0–A8 protocol: baseline,
  static audit, mutation testing of the risky modules in disposable copies,
  survivor triage, and cards for the real gaps (ADR-0016).
- **Which `.context/`.** The skills use `--context-dir`, else
  `$RUP_CONTEXT_DIR`, else the nearest `.context/` up to the git root. Curated
  docs are never touched.
- **What the skills never run.** They never run git; branch, commit and merge
  stay with you. They never run your tests either, except `cp-test --mutate`,
  which runs them only in temporary copies of the project.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error, invalid document/card (missing required artifacts), rejected delivery, invalid sizing model |
| 4 | `.context/` not writable |
| 5 | Needs authorization: `.context/` lacks the `.rup-standard` marker. The agent asks the user, then runs `cp-context --init` |

## Development

### Repository structure

```
core-poroduct-skills/
├── README.md                 # This file
├── LICENSE                   # MIT
├── CLAUDE.md / AGENT.md      # Context for coding agents working on this repo
├── requirements.txt          # Runtime dependencies: none (stdlib only)
├── requirements-dev.txt      # pytest
├── .github/workflows/ci.yml  # CI
├── .context/                 # Operational context (source of truth for agents)
├── tests/                    # Suite (no LLM, ~10 s)
├── scripts/install.sh        # Installs/updates the skills in the agents
└── skills/
    ├── README.md
    ├── _shared/              # helpers, not a skill
    │   ├── rup.py            # phases, ordered disciplines, exit codes
    │   ├── discipline.py     # work packet + --record engine
    │   ├── context.py        # .context/ resolution, writing, authorization marker
    │   ├── consent.py        # --status/--init/--import, pointer note
    │   ├── router.py         # front door: state of .context/ + routes (--route)
    │   ├── frontmatter.py    # card frontmatter parser/writer
    │   ├── cards.py          # cards, moves, roll-up, derivation
    │   ├── roadmap.py        # releases, iterations, generated views
    │   ├── testcheck*.py     # test-value checks (Python ast, JS/TS patterns)
    │   ├── testaudit.py      # static audit of a whole suite
    │   └── mutation.py       # mutation testing: mutants, runner, report, triage
    ├── cp-orchestrator/      # front door (--route), governance, iteration protocol, UCP
    ├── cp-<discipline>/      # SKILL.md + scripts/run.py (roles as data) + references/
    └── cp-{context,discover,backlog,build,debug,review}/   # execution skills
```

Edit the skills here, in `skills/`, never in the installed copy. Each `run.py`
finds `_shared/` next to the skill (repository, Claude Code) or one level up
(Hermes, which nests skills in a category directory). There are no hardcoded
OS/machine paths or personal values.

### Tests

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt
.venv/bin/python -m pytest                # Linux/macOS (.venv/Scripts/python.exe on Windows)
```

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | Every skill: stdlib only (`python -S`), packet with roles/artifacts/record command, exit 1 on missing briefing or unreadable `--input`, `SKILL.md` teaches `--record`, well-formed specs (9 document skills, 21 roles). Orchestrator: registry == skill dirs, `--list`, `--discipline`, `--auto` protocol order, sizing instructions; UCP exact/validated/CLI. `install.sh` plan and installed copies running in the Claude and Hermes layouts |
| `tests/test_context_persistence.py` | `.context/` resolution, layout, provenance, log, curated docs untouched; `--record` per skill (file/stdin), rejection of missing artifacts, exit 4; packets read-only; chaining in RUP order and per phase, cap on earlier artifacts; `--status`; caller's project resolution; sizing artifact; guard that the suite never writes into this repo |
| `tests/test_router.py` | Front door: routing packet (request, state, every route, chains), read-only, works without consent, suggestion order, broken cards, pointer-note refresh |
| `tests/test_consent.py`, `tests/test_rup_context.py` | Authorization marker and exit 5 on writing commands, non-destructive `--init`/upgrade, pointer note, import leaves originals untouched |
| `tests/test_frontmatter.py`, `tests/test_cards.py`, `tests/test_roadmap.py` | Card parser/writer, IDs, criteria, moves, History, roll-up, derivation, roadmap files and generated views |
| `tests/test_testcheck.py`, `tests/test_rup_{discover,build,debug,review}.py` | Test-value checks (trivial tests, criterion links, red evidence), start/finish with good and bad deliveries, bug flow, review verdicts |
| `tests/test_rup_test_audit.py` | cp-test audit: mutant generator, runner (kill/survive/timeout/error, resume, changed-tree refusal, budget, lines), report, triage rules, static audit, CLI and consent; mutation steps in cp-build/cp-review/cp-debug/orchestrator |
| `tests/test_higiene.py` | No committed secrets, no machine paths in code |

CI (`.github/workflows/ci.yml`) runs Python 3.12/3.13 on Linux (blocking) and
Windows (informative), plus `install.sh --dry-run`. It runs on pushes to `main`
and on PRs.

Questions, bugs or ideas: open an issue in this repository.

## License

[MIT](LICENSE) © 2026 Renato Sacramento Horta.
