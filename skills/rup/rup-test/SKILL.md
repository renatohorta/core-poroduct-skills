---
name: rup-test
description: "RUP Test Discipline (6/9). This skill covers the RUP **Test Discipline**: test planning, analysis, design, execution and evaluation. Use when the user says 'test plan, test cases, test strategy, run tests, test evaluation' or needs the RUP test artifacts."
---

# rup-test — RUP Test Discipline

This skill covers the RUP **Test Discipline**: test planning, analysis, design, execution and evaluation.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (4)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `test-manager` | Test Manager | Test Plan, Test Evaluation Summary |
| `test-analyst` | Test Analyst | Test Ideas List, Test Cases, Test Data, Workload Analysis Model |
| `test-designer` | Test Designer | Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification |
| `tester` | Tester | Test Scripts, Test Suites, Test Log, Test Results |

## Phase focus

Elaboration → Transition

## Usage

```bash
# Run the whole discipline crew
python scripts/run.py "briefing for the Test discipline"

# Target a specific RUP phase
python scripts/run.py "briefing" --phase Inception

# Inspect the crew without an LLM
python scripts/run.py "briefing" --phase Inception --dry-run

# From a context file
python scripts/run.py --input context.txt --output test.md
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
