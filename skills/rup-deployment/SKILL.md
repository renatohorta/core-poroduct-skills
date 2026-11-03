---
name: rup-deployment
description: "RUP Deployment Discipline (8/9). This skill covers the RUP **Deployment Discipline**: releasing the product and producing the user and training documentation. Use when the user says 'deploy, release notes, installation, user manual, training material' or needs the RUP deployment artifacts."
---

# rup-deployment — RUP Deployment Discipline

This skill covers the RUP **Deployment Discipline**: releasing the product and producing the user and training documentation.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (2)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `deployment-manager` | Deployment Manager | Deployment Plan, Installation Material, Release Description / Release Notes |
| `technical-writer` | Technical Writer | User Manual / User Documentation, Training Material |

## Phase focus

Construction → Transition

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Deployment discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output deployment.md
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
