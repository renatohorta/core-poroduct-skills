# Software Factory Architecture

The Software Factory is a set of CrewAI skills that orchestrate specialized
agents to run the complete software development cycle — from requirement to
delivery — with quality gates between phases.

## Overview

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
