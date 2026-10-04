# rup — Rational Unified Process family

A family of CrewAI skills implementing the **RUP (Rational Unified Process)** as
an autonomous team of agents, strictly grounded in *The Rational Unified Process:
An Introduction* (3rd ed.), Philippe Kruchten (Addison-Wesley / IBM Rational
Software).

The user interacts exclusively with `rup-orchestrator`, which governs the
lifecycle and dispatches the 8 discipline skills. Together they cover the **9 RUP
disciplines** and **21 agents** (1 orchestrator + 20 specialists).

## Disciplines

| Skill | Discipline | Agents | Agent slugs |
|-------|------------|--------|-------------|
| `rup-orchestrator` | Project Management (governance) | 1 | `rup-orchestrator` |
| `rup-environment` | Environment | 1 | `process-engineer` |
| `rup-business-modeling` | Business Modeling | 2 | `business-process-analyst`, `business-designer` |
| `rup-requirements` | Requirements | 2 | `system-analyst`, `requirements-specifier` |
| `rup-analysis-design` | Analysis & Design | 5 | `software-architect`, `designer`, `user-interface-designer`, `database-designer`, `capsule-designer` |
| `rup-implementation` | Implementation | 2 | `system-integrator`, `implementer` |
| `rup-test` | Test | 4 | `test-manager`, `test-analyst`, `test-designer`, `tester` |
| `rup-ccm` | Configuration & Change Management | 2 | `configuration-manager`, `change-control-manager` |
| `rup-deployment` | Deployment | 2 | `deployment-manager`, `technical-writer` |

## Lifecycle

```
Inception --> Elaboration --> Construction --> Transition
   LCO            LCA              IOC             PR
```

## Structure

```
skills/rup/
├── _shared/llm.py            # shared LLM helper (provider-agnostic)
├── rup-orchestrator/         # governance + dispatcher
│   ├── SKILL.md
│   ├── scripts/run.py
│   └── references/lifecycle.md
├── rup-environment/          # discipline 1
├── rup-business-modeling/    # discipline 2
├── rup-requirements/         # discipline 3
├── rup-analysis-design/      # discipline 4
├── rup-implementation/       # discipline 5
├── rup-test/                 # discipline 6
├── rup-ccm/                  # discipline 7
└── rup-deployment/           # discipline 8
```

Each discipline skill follows the repository convention: `SKILL.md` +
`scripts/run.py` (self-contained CrewAI crew, embedded agents) +
`references/agents.md` (agent → artifact mapping).

## CLI contract

```bash
# any discipline skill
python scripts/run.py "briefing" --phase Elaboration [--input F] [--output F] [--dry-run]

# the orchestrator adds --discipline, --auto and --list
python scripts/run.py "briefing" --discipline requirements
python scripts/run.py "briefing" --auto
python scripts/run.py --list

# Software Sizing & Effort Estimation (Use Case Points) — deterministic, no LLM
python scripts/run.py --sizing-template > sizing.json
python scripts/run.py --estimate --sizing sizing.json [--json]
```

Exit codes: `0` success · `1` usage error · `2` no LLM configured · `3` `crewai`
not installed. `--help` and `--dry-run` always work without credentials; the
sizing estimator (`--estimate`, `--sizing-template`) needs no crewai or LLM.

## Software sizing (owned by the orchestrator)

The orchestrator produces **Software Sizing & Effort Estimation** — Function
Points (IFPUG/NESMA), **Use Case Points** (UAW/UUCW/UUCP/TCF/EF) and parametric
estimates (COCOMO II, SLOC/KLOC) — feeding the Measurement Plan and the
Iteration Plan. The UCP calculation is implemented deterministically in
`rup-orchestrator/scripts/run.py` (`compute_ucp`) and can be run from the CLI.
Details and formulas: `rup-orchestrator/references/sizing-estimation.md`.

## Provenance

Generated from `~/Downloads/especificacao_agentes_rup.md`, which defines the 9
disciplines, the 20 agents (base RUP roles, missions and artifacts), the
4-phase lifecycle mapping (section 3) and the traceability matrix (section 5).
