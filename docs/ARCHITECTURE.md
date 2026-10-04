# Architecture

The repository hosts two skill families under `skills/`:

| Family | Path | Status | Installed by default? |
|--------|------|--------|-----------------------|
| **RUP** (`rup-*`) | `skills/rup/` | ✅ Active | ✅ Yes |
| **Software Factory** (`cp-*`) | `skills/deprecated/` | ⚠️ Deprecated | ❌ Only with `--deprecated` |

## Active family — RUP (`skills/rup/`)

A family of CrewAI skills implementing the **Rational Unified Process** as an
autonomous team of agents (Kruchten, 3rd ed.). The user interacts exclusively
with `rup-orchestrator`, which governs the lifecycle and dispatches the 8
discipline skills. **9 disciplines, 21 agents** (1 orchestrator + 20 specialists).

```
                    ┌─────────────────────────────┐
                    │   rup-orchestrator          │
                    │   (Project Manager)         │
                    │   - plans phases/iterations  │
                    │   - maintains SDP/Risk/Case │
                    │   - emits Work Orders       │
                    └─────────────┬───────────────┘
                                  │ Work Orders → subprocess dispatch
   ┌───────────┬───────────┬──────┴────┬───────────┬───────────┬──────────┐
   ▼           ▼           ▼           ▼           ▼           ▼          ▼
rup-env  rup-business  rup-req  rup-analysis  rup-impl   rup-test  rup-ccm  rup-deploy
(1)      -modeling(2)  (2)      -design(5)    (2)        (4)       (2)      (2)
```

Each discipline skill is self-contained: `SKILL.md` + `scripts/run.py` (embedded
agents + argparse) + `references/agents.md` (agent → artifact mapping). The
orchestrator dispatches a discipline by its `scripts/run.py` via `subprocess`,
respecting the shared CLI: `run.py "<briefing>" --phase <P> [--input] [--output]`.

The `_shared/llm.py` helper resolves the LLM provider-agnostically (same
resolution order as the deprecated family below). The orchestrator also ships a
deterministic **Use Case Points** estimator (`compute_ucp`, CLI `--estimate` /
`--sizing-template`) that runs with no LLM or crewai, producing the *Software
Sizing & Effort Estimation* artifact (see
`rup-orchestrator/references/sizing-estimation.md`).

Structure and provenance: [`skills/rup/README.md`](../skills/rup/README.md).

---

## Deprecated family — Software Factory (`skills/deprecated/`)

> ⚠️ **DEPRECATED MODE** — the `cp-*` skills described here live in
> **`skills/deprecated/`** and are no longer installed or orchestrated by default.
> This section records the historical architecture; it is not an active pipeline.

The Software Factory is a set of CrewAI skills that orchestrate specialized
agents to run the complete software development cycle — from requirement to
delivery — with quality gates between phases.

## Overview

> All `cp-*` skills referenced below are in **deprecated mode** under
> `skills/deprecated/`. The diagram records the historical wiring.

```
                    ┌─────────────────────────────┐
                    │     cp-orchestrator         │
                    │  (Factory Manager)          │
                    │  - coordinates crews        │
                    │  - manages artifacts         │
                    │  - applies quality gates     │
                    └─────────────┬───────────────┘
                                  │ triggers (modes)
        ┌────────────┬────────────┼────────────┬──────────────┐
        ▼            ▼            ▼            ▼              ▼
   [Pipeline]   [Complementary] [NEXUS]   [Carousels]   [Analysis]
   cp-requirements cp-bug-fix      full-dev   universal-     cp-competitive-
   cp-architecture cp-goal-loop   (native)   carousel       analysis
   cp-implementation cp-maintenance           instagram-
   cp-testing                                  carousel-
   cp-security                               generator
   cp-devops
   cp-software-spec
   cp-quality
```

## Main pipeline (`full` mode)

```
[Requirements] → [Architecture] → [Implementation] → [Testing] → [Security] → [DevOps] → [Documentation] → [Quality] → [Delivery]
     │              │                │              │           │            │             │              │
 cp-requirements  cp-architecture  cp-implementation cp-testing  cp-security cp-devops  cp-software-spec cp-quality
     │              │                │              │           │            │             │              │
 [Quality Gate] [Quality Gate]  [Quality Gate] [Quality Gate][Quality Gate][Quality Gate][Quality Gate][Quality Gate]
```

Each phase produces an artifact that feeds the next. The quality gate decides:
- **PASS** → advances
- **WARN** → advances with documented caveats
- **FAIL** → stops the pipeline

## Operation modes

| Mode | Crews | Use |
|------|-------|-----|
| `full` | 8 pipeline phases | Complete project |
| `sprint` | requirements → architecture → implementation → testing → devops | Feature |
| `micro` | implementation → testing | Quick bug fix |
| `security-audit` | security → quality | Security audit |
| `documentation` | documentation → quality | Documentation |
| `bugfix` | cp-bug-fix | Bug fix |
| `competitive` | cp-competitive-analysis | Competitive intelligence |
| `full-dev` | native NEXUS | Complete NEXUS pipeline |
| `goal-loop` | cp-goal-loop | Autonomous loop |
| `maintenance` | cp-maintenance | Maintenance/evolution |

## NEXUS pipeline (native in the orchestrator)

The `cp-full-dev` was **merged** into `cp-orchestrator`. The NEXUS pipeline (7
phases, 39 agents) runs natively via `NexusExecutor`:

```
Discovery → Strategy → Foundation → Build → Hardening → Launch → Operate
```

With automatic mode detection (full/sprint/micro) and per-phase quality gates.

## Trigger contract (`invoke` metadata)

Each crew in the orchestrator carries `invoke` metadata that describes how the
skill is triggered via CLI:

- `briefing_arg`: `positional` (positional arg), `goal` (`--goal`), or `input` (`--input`)
- `output`: `True` if the skill accepts `--output`, `False` otherwise

This ensures the orchestrator calls each skill respecting its real interface.

## Portability

All skills are portable:
- **Zero hardcoded OS/machine paths** (C:\Windows, C:\Users, etc.)
- **Zero fixed personal values** (handles, machine names)
- Project paths use env vars + relative defaults
