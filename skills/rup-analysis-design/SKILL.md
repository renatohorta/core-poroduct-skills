---
name: rup-analysis-design
description: "RUP Analysis & Design Discipline (4/9). This skill covers the RUP **Analysis & Design Discipline**: the architecture (4+1 views), the detailed design model, and the UI, data and capsule designs. Use when the user says 'architecture, SAD 4+1, design model, data model, UI design, capsules' or needs the RUP analysis & design artifacts."
---

# rup-analysis-design — RUP Analysis & Design Discipline

This skill covers the RUP **Analysis & Design Discipline**: the architecture (4+1 views), the detailed design model, and the UI, data and capsule designs.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (5)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `software-architect` | Software Architect | Software Architecture Document (SAD) — 4+1 Views, Architectural Prototype / Proof-of-Concept, Design Guidelines |
| `designer` | Designer | Design Model, Use-Case Realizations, Design Classes, Design Subsystems & Design Packages, Interfaces, Analysis Model |
| `user-interface-designer` | User-Interface Designer | Storyboards, Navigation Map, User-Interface Prototype |
| `database-designer` | Database Designer | Data Model, Object-Relational Mapping |
| `capsule-designer` | Capsule Designer | Capsules, Protocols, Events & Signals |

## Phase focus

Elaboration → Construction

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Analysis & Design discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output analysis-design.md
```

## CLI contract

| Argument | Meaning |
|----------|---------|
| `briefing` (positional) | Business demand / context for the discipline |
| `--input <file>` | Read the briefing from a file (alternative to positional) |
| `--phase {Inception,Elaboration,Construction,Transition}` | RUP phase (default: Elaboration) |
| `--output <file>` | Write the result to a file |
| `--dry-run` | Build the crew and list the agents, without calling an LLM |

Exit codes: `0` success · `1` usage error · `2` no LLM configured · `3` `crewai`
not installed. `--help` and `--dry-run` always work without credentials.

## Reference

Agent → artifact mapping and missions: `references/agents.md`.
