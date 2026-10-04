---
name: rup-implementation
description: "RUP Implementation Discipline (5/9). This skill covers the RUP **Implementation Discipline**: incremental integration planning and coding with developer tests. Use when the user says 'implement, code, integrate, build, developer tests' or needs the RUP implementation artifacts."
---

# rup-implementation — RUP Implementation Discipline

This skill covers the RUP **Implementation Discipline**: incremental integration planning and coding with developer tests.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (2)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `system-integrator` | System Integrator | Integration Build Plan, Build |
| `implementer` | Implementer | Implementation Elements, Implementation Subsystems, Developer Tests, Test Stubs & Testability Elements |

## Phase focus

Elaboration → Construction

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Implementation discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output implementation.md
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
