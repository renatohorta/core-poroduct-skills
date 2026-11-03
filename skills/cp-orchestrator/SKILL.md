---
name: cp-orchestrator
description: "RUP-Orchestrator — single point of contact for the Rational Unified Process lifecycle. Classifies demands into RUP phases (Inception/Elaboration/Construction/Transition), maintains the Software Development Plan, Business Case and Risk List, emits formal Work Orders and drives the 8 discipline skills (20 specialized RUP roles) — the agent running the skill is the LLM; artifacts are recorded in .context/. Use when the user says 'run RUP', 'rational unified process', 'plan the iteration', 'manage the project', 'work orders', or wants the full RUP lifecycle governed end to end."
---

# cp-orchestrator — RUP Lifecycle Governance

Central orchestrator of the **RUP (Rational Unified Process)** family. The user
dialogues exclusively with this skill; it plans phases and iterations, manages
risks, formulates formal **Work Orders** and drives the discipline skills.

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
| `cp-environment` | Environment | 1 | `process-engineer` |
| `cp-business-modeling` | Business Modeling | 2 | `business-process-analyst`, `business-designer` |
| `cp-requirements` | Requirements | 2 | `system-analyst`, `requirements-specifier` |
| `cp-analysis-design` | Analysis & Design | 5 | `software-architect`, `designer`, `user-interface-designer`, `database-designer`, `capsule-designer` |
| `cp-implementation` | Implementation | 2 | `system-integrator`, `implementer` |
| `cp-test` | Test | 4 | `test-manager`, `test-analyst`, `test-designer`, `tester` |
| `cp-ccm` | Configuration & Change Management | 2 | `configuration-manager`, `change-control-manager` |
| `cp-deployment` | Deployment | 2 | `deployment-manager`, `technical-writer` |

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

## How to run this skill — you are the LLM

This skill never calls a model: **you, the agent running it, write every
artifact**. The script prints work packets/protocols, records your documents
into `.context/` (mandatory) and computes Use Case Points exactly.

### One step (governance or one discipline)

1. Get the work packet (read-only):
   `python scripts/run.py "<briefing>" --phase Inception` (governance) or
   `python scripts/run.py "<briefing>" --discipline requirements`.
2. Write ONE markdown document: `# <Role>` per role, `## <Artifact>` for every
   artifact the packet lists.
3. Record it — mandatory; the packet prints the exact command
   (`… --record doc.md --phase P "<briefing>"`, or `--record -` for stdin). A
   discipline is recorded with **its own** skill's `run.py`. Missing artifacts →
   exit `1`, nothing written: add them and record again.

### A whole iteration

`python scripts/run.py "<briefing>" --auto --phase Elaboration` prints the
protocol: governance (step 0) + the 8 disciplines, in RUP order, each with its
packet command. Do the three steps above for each, **in order** — every packet
embeds what the earlier steps recorded in `.context/`, which is how the
disciplines build on each other. `--status` shows what is recorded and the next
pending step (use it to resume).

### Sizing — never compute UCP yourself

```bash
python scripts/run.py --sizing-template > sizing.json         # fill actors/use cases/factors
python scripts/run.py --estimate --sizing sizing.json --phase Inception   # [--json]
```

`--estimate` prints UAW/UUCW/UUCP/TCF/EF/UCP/effort and records
`cp-orchestrator-sizing.md`; copy those numbers into the governance document.
FPA (IFPUG/NESMA) and COCOMO II/SLOC are your estimates — show inputs and arithmetic.

## CLI contract

| Argument | Meaning |
|----------|---------|
| `briefing` (positional) / `--input <file>` | Business demand / product direction |
| `--phase {Inception,Elaboration,Construction,Transition}` | RUP phase (default: Elaboration) |
| `--context-dir <dir>` | The `.context/` (default: `$RUP_CONTEXT_DIR`, else the nearest up to the git root) |
| `--record <file\|->` | Validate your governance document and write it to `.context/` |
| `--discipline <key>` | Print that discipline's work packet |
| `--auto` | Print the iteration protocol (governance + 8 disciplines, in order) |
| `--status` | Show which steps are recorded in `.context/` for the phase |
| `--list` | List the disciplines |
| `--estimate [--sizing F] [--json]` | Use Case Points (deterministic), recorded in `.context/` |
| `--sizing-template` | Print an empty JSON sizing model |

Exit codes: `0` success · `1` usage error / missing artifacts / invalid sizing
model · `4` `.context/` not writable. Standard library only — no LLM key, no `crewai`.

## Artifacts in `.context/` (mandatory)

| What | File |
|------|------|
| Governance | `.context/docs/<NN-phase>/cp-orchestrator.md` |
| UCP estimate | `.context/docs/<NN-phase>/cp-orchestrator-sizing.md` |
| Each discipline | `.context/docs/<NN-phase>/cp-<discipline>.md` |
| Every write | a row in `.context/tracking/rup-log.md` |

Each file has a provenance header (skill, phase, milestone, timestamp, briefing
excerpt) and is regenerated per run (history in git). Curated docs
(`requirements.md`, …) are never touched.

## Reference

Lifecycle, phases, milestones and the artifact matrix: `references/lifecycle.md`.
Sizing techniques and the UCP formulas: `references/sizing-estimation.md`.
