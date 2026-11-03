---
name: rup-ccm
description: "RUP Configuration & Change Management Discipline (7/9). This skill covers the RUP **Configuration & Change Management Discipline**: baselines, workspace policy and formal Change Requests. Use when the user says 'configuration management, baselines, change request, CCB' or needs the RUP configuration & change management artifacts."
---

# rup-ccm — RUP Configuration & Change Management Discipline

This skill covers the RUP **Configuration & Change Management Discipline**: baselines, workspace policy and formal Change Requests.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (2)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `configuration-manager` | Configuration Manager | Configuration Management Plan, Baselines |
| `change-control-manager` | Change Control Manager | Change Request (CR) |

## Phase focus

All phases

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Configuration & Change Management discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output ccm.md
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
