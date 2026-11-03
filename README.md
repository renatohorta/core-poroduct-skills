# Core Product Skills

Central repository for the **skills** propagated to the **Hermes Agent** and
**Claude Code** — the **single source of truth**: any change is made here and then
propagated to the agents via `scripts/install.sh`.

The skills implement the **Rational Unified Process (RUP)** — 9 disciplines, 21
roles — grounded in *The Rational Unified Process: An Introduction* (3rd ed.),
Philippe Kruchten.

**The agent running a skill is the LLM** (ADR-0012). The skills never call a
model and have no runtime dependency (standard library only): they hand the agent
a *work packet* — the RUP roles, missions, required artifacts and the context
already recorded — and then validate and record the agent's document into the
project's `.context/` (mandatory, ADR-0011). No API key, no proxy, no CrewAI: the
same model, with the same conversation context, writes the artifacts.

> History: the legacy `cp-*` family was removed (ADR-0010); the CrewAI execution
> of the RUP skills was replaced by the host-LLM model (ADR-0012). Both remain in
> the git history.

## The RUP skills (`skills/rup-*`)

| Skill | Discipline | Roles |
|-------|------------|-------|
| `rup-orchestrator` | Project Management (governance) | 1 |
| `rup-environment` | Environment | 1 |
| `rup-business-modeling` | Business Modeling | 2 |
| `rup-requirements` | Requirements | 2 |
| `rup-analysis-design` | Analysis & Design | 5 |
| `rup-implementation` | Implementation | 2 |
| `rup-test` | Test | 4 |
| `rup-ccm` | Configuration & Change Management | 2 |
| `rup-deployment` | Deployment | 2 |

Full details: [`skills/README.md`](skills/README.md) and [`docs/SKILLS.md`](docs/SKILLS.md).

## How a skill runs

```
agent ──► run.py "<briefing>" --phase P        ─► WORK PACKET (read-only)
                                                   roles · missions · required artifacts
                                                   briefing · earlier .context/ artifacts
agent writes ONE document: "# <Role>" + "## <Artifact>" for each required artifact
agent ──► run.py --record doc.md --phase P     ─► validates every "## <Artifact>"
                                                   writes .context/docs/<NN-phase>/rup-<skill>.md
                                                   logs   .context/tracking/rup-log.md
```

- **Chaining**: a discipline's packet embeds the governance artifact and the
  artifacts of the earlier disciplines recorded in the same phase. Run them in
  order and each builds on the previous ones.
- **Whole iteration**: `rup-orchestrator "<briefing>" --auto` prints the
  protocol (governance + 8 disciplines, in order, with the commands);
  `--status` shows what is recorded and the next pending step.
- **Sizing**: Use Case Points are computed by code (`--estimate`), never by the
  model; the governance packet tells the agent how.
- **Which `.context/`**: `--context-dir`, else `$RUP_CONTEXT_DIR`, else the
  nearest `.context/` up to the git root. Curated docs (`requirements.md`, …)
  are never touched — generated artifacts carry the `rup-` prefix.

## Repository structure

```
core-poroduct-skills/
├── README.md                 # This file
├── CLAUDE.md / AGENT.md      # Context for coding agents working on this repo
├── requirements.txt          # Runtime dependencies: none (stdlib only)
├── requirements-dev.txt      # pytest
├── .github/workflows/ci.yml  # CI
├── .context/                 # Operational context (source of truth for agents)
├── tests/                    # Suite (no LLM, ~3 s)
├── docs/                     # INSTALLATION, ARCHITECTURE, SKILLS
├── scripts/install.sh        # Installs/updates the skills in the agents
└── skills/
    ├── README.md
    ├── _shared/              # helpers, not a skill
    │   ├── rup.py            # phases, ordered disciplines, exit codes
    │   ├── discipline.py     # work packet + --record engine
    │   └── context.py        # .context/ resolution and writing
    ├── rup-orchestrator/     # governance, iteration protocol, UCP
    └── rup-<discipline>/     # SKILL.md + scripts/run.py (roles as data) + references/
```

## Quick install

```bash
./scripts/install.sh                       # every skill, Hermes + Claude
./scripts/install.sh --hermes | --claude   # one agent
./scripts/install.sh --skill rup-requirements
./scripts/install.sh --dry-run
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Development and testing

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt
.venv/bin/python -m pytest                # Linux/macOS (.venv/Scripts/python.exe on Windows)
```

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | Every skill: stdlib only (`python -S`), packet with roles/artifacts/record command, exit 1 on missing briefing or unreadable `--input`, `SKILL.md` teaches `--record`, well-formed specs (9 skills, 21 roles). Orchestrator: registry == skill dirs, `--list`, `--discipline`, `--auto` protocol order, sizing instructions; UCP exact/validated/CLI. `install.sh` plan and installed copies running in the Claude and Hermes layouts |
| `tests/test_context_persistence.py` | `.context/` resolution, layout, provenance, log, curated docs untouched; `--record` per skill (file/stdin), rejection of missing artifacts, exit 4; packets read-only; chaining in RUP order and per phase, cap on earlier artifacts; `--status`; caller's project resolution; sizing artifact; guard that the suite never writes into this repo |
| `tests/test_higiene.py` | No committed secrets, no machine paths in code |

CI (`.github/workflows/ci.yml`): Python 3.12/3.13 on Linux (blocking) and Windows
(informative), plus `install.sh --dry-run`, on pushes to `main` and on PRs.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error: missing briefing, unreadable `--input`, document missing required artifacts, invalid sizing model |
| 4 | `.context/` not writable |

## Portability

No hardcoded OS/machine paths or personal values. Each `run.py` finds `_shared/`
next to the skill (repository, Claude Code) or one level up (Hermes, which nests
skills in a category directory).

## License

Internal use. © Renato Sacramento Horta.
