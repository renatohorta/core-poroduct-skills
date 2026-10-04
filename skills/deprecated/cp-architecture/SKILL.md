---
name: cp-architecture
description: "Software Architecture and Design — creates a CrewAI crew with Software Architect, Data Architect, API Architect, UX Architect and Technical Reviewer to define architecture, model data, design APIs and validate decisions. Use when the user says 'define architecture', 'model data', 'design API', 'create ADR', 'do system design'."
---

# cp-architecture — Software Architecture and Design

Creates a CrewAI crew with specialized agents to run the complete software architecture and design cycle:

1. **Software Architect** — Defines architecture (monolith, microservices, modular monolith), patterns, architectural decisions
2. **Data Architect** — Models database, schema, migrations, indexes
3. **API Architect** — Designs REST/GraphQL contracts, OpenAPI, versioning
4. **UX Architect** — Designs user flows, prototypes, journeys
5. **Technical Reviewer** — Validates architectural decisions, identifies risks, suggests alternatives

## Agents

| Agent | Role |
|--------|--------|
| Software Architect | Defines architecture, patterns, architectural decisions (ADRs) |
| Data Architect | Models database, schema, migrations, indexes |
| API Architect | Designs REST/GraphQL contracts, OpenAPI, versioning |
| UX Architect | Designs user flows, prototypes, journeys |
| Technical Reviewer | Validates decisions, identifies risks, suggests alternatives |

## Input

Requirements document or system briefing — problem description, features, constraints. Can be:
- Direct text in the argument: `"scheduling system for clinics"`
- File: `--input requirements.md`

## Output

Complete architecture document containing:
- **Architectural Decisions (ADRs)** — context, decision, consequences
- **C4 Diagram** (levels 1-2: context and containers)
- **Data Schema** — entities, relationships, indexes
- **API Contracts** — endpoints, payloads, versioning
- **User Flows** — journeys, navigation prototypes
- **Quality Gate** — Technical Reviewer PASS/FAIL verdict

## Quality Gate

The Technical Reviewer issues a PASS/FAIL verdict. If FAIL, the document needs fixes before moving to implementation.

## Usage

```bash
# Direct briefing
python .hermes/skills/cp-architecture/scripts/run.py "scheduling system for clinics"

# Briefing from file
python .hermes/skills/cp-architecture/scripts/run.py --input requirements.md

# Save output to a specific file
python .hermes/skills/cp-architecture/scripts/run.py "inventory app" --output docs/architecture.md

# Just view the crew structure
python .hermes/skills/cp-architecture/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-architecture/scripts/run.py \
  "scheduling system for aesthetics clinics with online scheduling, \
   management of the aesthetician's schedule, revenue reports for the owner, \
   and automatic WhatsApp reminders. Needs to be web, multi-clinic, \
   with monthly subscription plans."
```

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.
