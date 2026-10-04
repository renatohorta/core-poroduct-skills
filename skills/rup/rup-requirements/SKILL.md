---
name: rup-requirements
description: "RUP Requirements Discipline (3/9). This skill covers the RUP **Requirements Discipline**: eliciting, specifying and validating the system's requirements (Vision → SRS). Use when the user says 'gather requirements, vision document, use cases, SRS, FURPS, glossary' or needs the RUP requirements artifacts."
---

# rup-requirements — RUP Requirements Discipline

This skill covers the RUP **Requirements Discipline**: eliciting, specifying and validating the system's requirements (Vision → SRS).

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (2)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `system-analyst` | System Analyst | Stakeholder Requests, Vision Document, Use-Case Model Survey, System Actors, Glossary, Requirements Management Plan |
| `requirements-specifier` | Requirements Specifier | Use Cases, Use-Case Packages, Supplementary Specifications (FURPS), Software Requirements Specification (SRS), Requirements Attributes |

## Phase focus

Inception → Elaboration

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Requirements discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output requirements.md
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
