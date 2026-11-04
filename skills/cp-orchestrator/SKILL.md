---
name: cp-orchestrator
description: "RUP-Orchestrator — the FRONT DOOR of the cp-* skills and single point of contact for the RUP lifecycle. Routes any plain request about the project (a new idea or feature, requirements, backlog, implement a task, a bug, a review, test quality, status, what next) to the right cp-* skill and runs it — the user never has to name a skill. Also classifies demands into RUP phases, maintains the Software Development Plan, Business Case and Risk List, emits Work Orders and drives the 8 discipline skills — the agent running the skill is the LLM; artifacts are recorded in .context/. Use whenever the user asks for software-project work without naming a specific cp-* skill, says 'what now / continue', or says 'run RUP', 'plan the iteration', 'manage the project', 'work orders'."
---

# cp-orchestrator — RUP Lifecycle Governance

Central orchestrator of the **RUP (Rational Unified Process)** family. The user
dialogues exclusively with this skill; it plans phases and iterations, manages
risks, formulates formal **Work Orders** and drives the discipline skills.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Base role: **Project Manager** (supported by the Project Reviewer).

## Front door — start every request here

The user talks in plain words ("quero login com Google", "o checkout quebrou",
"revisa o TK-012", "e agora?"). They **never** have to know or call a cp-*
skill: you route the request and run the skills yourself.

```bash
python scripts/run.py --route "<what the user asked>"
```

The routing packet (read-only) shows the project state from `.context/`
(authorization, discovery, requirements, board, open bugs), a **suggested next
step**, every route with its exact command, and the standard chains:

| Request | Chain you run |
|---|---|
| New product / feature / epic | `cp-discover` → requirements → `cp-backlog --derive` → *user confirms cards* → `cp-build` → `cp-review` |
| Bug | `cp-debug --open` → failing test → `--diagnose` → `cp-build` → `cp-review` |
| Small clear change | `cp-backlog --new task` → `cp-build` → `cp-review` |
| "Are the tests any good?" | `cp-test --audit` → cards for the real gaps → `cp-build` |
| "What now?" / "continue" | the suggested next step |

Rules: say in one line what you will do, run the command, follow its packet, and
continue the chain on your own. Stop for the user only at the gates —
authorizing `.context/` (exit 5), the discovery conversation, confirming derived
cards, a real ambiguity between two routes (one question, with your
suggestion), and anything destructive or outward-facing. Never answer "call
cp-xxx".

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
| `--route` | Front door: routing packet for the request (state, suggestion, routes, chains); read-only |
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
