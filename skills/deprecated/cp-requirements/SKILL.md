---
name: cp-requirements
description: "Requirements Engineering — creates a CrewAI crew with Business Analyst, Specifier, Validator and PO Proxy to elicit, specify, validate and prioritize software requirements. Use when the user says 'gather requirements', 'specify', 'document requirements', 'do business analysis', 'create user stories', or needs to turn a briefing into a requirements document."
---

# cp-requirements — Requirements Engineering

Creates a CrewAI crew with specialized agents to run the complete requirements engineering cycle:

1. **Business Analyst** — Elicitation: interviews the briefing, discovers business rules, stakeholders, risks
2. **Requirements Specifier** — Specification: user stories, use cases, acceptance criteria (BDD), non-functional requirements
3. **Requirements Validator** — Validation: checks completeness, consistency, clarity, testability, feasibility
4. **Product Owner (Proxy)** — Prioritization: MoSCoW, MVP definition, dependencies

## Agents

| Agent | Role |
|--------|--------|
| Business Analyst | Interviews stakeholders, discovers implicit business rules |
| Requirements Specifier | Writes user stories, use cases, acceptance criteria |
| Requirements Validator | Checks consistency, completeness, feasibility |
| Product Owner (Proxy) | Prioritizes and validates alignment with the product vision |

## Input

Client briefing — problem description, domain, needs. Can be:
- Direct text in the argument: `"scheduling system for clinics"`
- File: `--input briefing.txt`

## Output

Complete requirements document containing:
- Business analysis (stakeholders, rules, risks)
- Epics and features
- User stories with acceptance criteria (BDD)
- Use cases (main flow + alternatives)
- Formal business rules
- Non-functional requirements
- Prioritized backlog (MoSCoW)
- MVP suggestion

## Quality Gate

The Requirements Validator issues a PASS/FAIL verdict. If FAIL, the document needs fixes before moving to the next phase.

## Usage

```bash
# Direct briefing
python .hermes/skills/cp-requirements/scripts/run.py "scheduling system for clinics"

# Briefing from file
python .hermes/skills/cp-requirements/scripts/run.py --input briefing.txt

# Save output to a specific file
python .hermes/skills/cp-requirements/scripts/run.py "inventory app" --output docs/requirements.md

# Just view the crew structure
python .hermes/skills/cp-requirements/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-requirements/scripts/run.py \
  "I need a system for an aesthetics clinic where the receptionist schedules clients, \
   the aesthetician sees her daily schedule, and the clinic owner wants revenue reports. \
   It also needs to send automatic WhatsApp reminders."
```

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.
