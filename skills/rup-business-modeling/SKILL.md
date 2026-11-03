---
name: rup-business-modeling
description: "RUP Business Modeling Discipline (2/9). This skill covers the RUP **Business Modeling Discipline**: understanding the target organization and designing the business processes the software supports. Use when the user says 'business vision, target organization, business processes, business use cases, business rules' or needs the RUP business modeling artifacts."
---

# rup-business-modeling — RUP Business Modeling Discipline

This skill covers the RUP **Business Modeling Discipline**: understanding the target organization and designing the business processes the software supports.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (2)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `business-process-analyst` | Business Process Analyst | Business Vision Document, Business Goals, Target-Organization Assessment, Business Use-Case Model, Business Actors, Business Glossary |
| `business-designer` | Business Designer | Business Analysis Model, Business Use-Case Realizations, Business Workers, Business Entities, Business Systems, Business Events, Business Rules, Supplementary Business Specifications, Business Architecture Document |

## Phase focus

Inception (initial), Elaboration

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Business Modeling discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output business-modeling.md
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
