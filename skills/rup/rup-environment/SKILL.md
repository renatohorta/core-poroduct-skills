---
name: rup-environment
description: "RUP Environment Discipline (1/9). This skill covers the RUP **Environment Discipline**: tailoring the process and producing the Development Case, guidelines and templates. Use when the user says 'tailor RUP, development case, process guidelines, project templates' or needs the RUP environment artifacts."
---

# rup-environment — RUP Environment Discipline

This skill covers the RUP **Environment Discipline**: tailoring the process and producing the Development Case, guidelines and templates.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (1)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `process-engineer` | Process Engineer | Development Case, Project-Specific Guidelines, Templates |

## Phase focus

All phases

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Environment discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output environment.md
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
