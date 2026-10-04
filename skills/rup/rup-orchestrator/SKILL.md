---
name: rup-orchestrator
description: "RUP-Orchestrator — single point of contact for the Rational Unified Process lifecycle. Classifies demands into RUP phases (Inception/Elaboration/Construction/Transition), maintains the Software Development Plan, Business Case and Risk List, emits formal Work Orders and dispatches the 8 discipline crews covering 20 specialized agents. Use when the user says 'run RUP', 'rational unified process', 'plan the iteration', 'manage the project', 'work orders', or wants the full RUP lifecycle governed end to end."
---

# rup-orchestrator — RUP Lifecycle Governance

Central orchestrator of the **RUP (Rational Unified Process)** family. The user
dialogues exclusively with this skill; it plans phases and iterations, manages
risks, formulates formal **Work Orders** and dispatches the discipline crews.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Base role: **Project Manager** (supported by the Project Reviewer).

## Lifecycle

```
Inception --> Elaboration --> Construction --> Transition
   LCO            LCA              IOC             PR
```

| Phase | Milestone |
|-------|-----------|
| Inception | Lifecycle Objective (LCO) |
| Elaboration | Lifecycle Architecture (LCA) |
| Construction | Initial Operational Capability (IOC) |
| Transition | Product Release (PR) |

## Disciplines and agents (20 specialist agents across 8 disciplines)

| Skill | Discipline | Agents | Agent slugs |
|-------|------------|--------|-------------|
| `rup-environment` | Environment | 1 | `process-engineer` |
| `rup-business-modeling` | Business Modeling | 2 | `business-process-analyst`, `business-designer` |
| `rup-requirements` | Requirements | 2 | `system-analyst`, `requirements-specifier` |
| `rup-analysis-design` | Analysis & Design | 5 | `software-architect`, `designer`, `user-interface-designer`, `database-designer`, `capsule-designer` |
| `rup-implementation` | Implementation | 2 | `system-integrator`, `implementer` |
| `rup-test` | Test | 4 | `test-manager`, `test-analyst`, `test-designer`, `tester` |
| `rup-ccm` | Configuration & Change Management | 2 | `configuration-manager`, `change-control-manager` |
| `rup-deployment` | Deployment | 2 | `deployment-manager`, `technical-writer` |

## Artifacts under the orchestrator's strict responsibility

- Software Development Plan (SDP)
- Risk Management Plan & Risk List
- Problem Resolution Plan
- Product Acceptance Plan
- Measurement Plan & Project Measurements Database
- **Software Sizing & Effort Estimation** — FPA (IFPUG/NESMA), Use Case Points
  (UAW/UUCW/UUCP/TCF/EF), COCOMO II / SLOC-KLOC
- Business Case
- Iteration Plan & Work Orders
- Iteration Assessment & Status Assessment

## Usage

```bash
# Governance: classify the demand, update the plan, emit Work Orders
python scripts/run.py "clinics scheduling SaaS" --phase Inception

# Inspect the plan without an LLM
python scripts/run.py "clinics scheduling SaaS" --phase Inception --dry-run

# Software Sizing & Effort Estimation — Use Case Points (no LLM needed)
python scripts/run.py --sizing-template > sizing.json     # empty model to fill in
python scripts/run.py --estimate --sizing sizing.json      # compute UCP + effort
python scripts/run.py --estimate --sizing sizing.json --json   # machine-readable

# Dispatch a single discipline
python scripts/run.py "briefing" --discipline requirements

# Dispatch every discipline in sequence
python scripts/run.py "briefing" --auto

# List the disciplines
python scripts/run.py --list
```

## CLI contract

| Argument | Meaning |
|----------|---------|
| `briefing` (positional) | Business demand / product direction |
| `--input <file>` | Read the briefing from a file |
| `--phase {Inception,Elaboration,Construction,Transition}` | RUP phase (default: Elaboration) |
| `--discipline <key>` | Dispatch only this discipline |
| `--auto` | Dispatch all disciplines in sequence |
| `--list` | List disciplines and exit |
| `--estimate` | Compute the Use Case Points sizing (no LLM) |
| `--sizing <file>` | JSON sizing model for `--estimate` |
| `--sizing-template` | Print an empty JSON sizing model and exit |
| `--json` | With `--estimate`: emit the result as JSON |
| `--output <file>` | Write the result to a file |
| `--dry-run` | Show the plan without calling an LLM |

Exit codes: `0` success · `1` usage error · `2` no LLM configured · `3` `crewai`
not installed. `--help`, `--list`, `--sizing-template` and `--estimate` always
work without credentials.

## Reference

Lifecycle, phases, milestones and the artifact matrix: `references/lifecycle.md`.
Sizing techniques and the UCP formulas: `references/sizing-estimation.md`.
