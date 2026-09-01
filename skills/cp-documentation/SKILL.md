---
name: cp-documentation
description: "Software Documentation — creates a CrewAI crew with Technical Writer, User Writer, Diagrammer and Reviewer to generate technical, API, user documentation and diagrams. Use when the user says 'document', 'create documentation', 'write README', 'generate API docs', 'create user manual'."
---

# cp-documentation — Software Documentation

Creates a CrewAI crew with specialized agents to generate complete software documentation:

1. **Technical Writer** — Writes technical and API documentation. Turns complex code into clear, useful documentation.
2. **User Writer** — Writes manuals, guides, FAQs, tutorials. Focus on the end user with simple language and practical examples.
3. **Diagrammer** — Creates diagrams, flowcharts, screenshots (Mermaid, PlantUML). Worth more than 1000 words.
4. **Documentation Reviewer** — Checks clarity, completeness, consistency, spelling. Doesn't let spelling errors or missing information pass.

## Pipeline (sequential tasks)

```
[Analysis] ──► [Technical + API Doc] ──► [User Doc] ──► [Diagrams] ──► [Review]
    │                │                       │                  │               │
    │  Technical     │  Technical Writer     │  User Writer    │  Diagrammer  │  Reviewer
    │  Writer        │                       │                  │              │
    │                │                       │                  │              │
    └────────────────┴───────────────────────┴──────────────────┴──────────────┴── PASS/FAIL
```

## Agents

| Agent | Role |
|--------|--------|
| Technical Writer | Analysis of what to document + technical and API documentation |
| User Writer | Manuals, guides, FAQs, tutorials for the end user |
| Diagrammer | Mermaid/PlantUML diagrams, flowcharts, visuals |
| Documentation Reviewer | Final review: clarity, completeness, consistency, spelling |

## Input

Description of what to document — can be:
- Source code (project path)
- APIs (endpoints, schemas)
- Functional requirements
- Direct text in the argument: `"scheduling API for clinics"`
- File: `--input description.txt`

## Output

Complete documentation containing:
- Main project README
- Technical documentation (architecture, components, decisions)
- API documentation (endpoints, schemas, examples)
- User guide (installation, configuration, usage)
- Diagrams (architecture, flow, entity-relationship)
- Reviewed and approved documentation

## Documenting an app's SCREENS (spec for Lovable/UI generator)

When the request is "specify all the system's screens to generate layout variations"
(in Lovable or similar), the inventory MUST NOT be driven only by routes. Real pitfall
that has already caught us: listing only `src/routes/*.tsx` leaves out the **dynamic**
components rendered on conversational surfaces (chat), which are first-class screens/cards
for the generator.

Complete inventory recipe:
1. **Routes (file-based)**: `src/routes/**/*.tsx` → one entry per route (listing method:
   `os.walk` in Python; on this host `search_files` fails if there's no ripgrep).
2. **Shared layout/shell**: the `AppShell`/layout (side rail + statusbar) is the
   skeleton that ALL internal screens share — document it once and mark which
   screens use it (internal) and which are fullscreen without rail (auth).
3. **Dynamic components / Generative UI**: any `registry` of cards that the backend
   renders inside the chat (`render_*_tool`, `uiPayload.component`) ARE screens for the
   generator. Inventory each card (header, body, states, actions) and the contract rule
   (e.g.: approval card only forwards the decision back to the backend).
4. **Mandatory design system**: define tokens (colors, fonts, recurring components)
   before the screens — that's what keeps the variations coherent.
5. **States per screen**: loading / error (with retry) / empty / populated — require all.
6. **Don't change scope**: variation is of layout, not of functionality.

Reuse the ready skeleton in `templates/spec-telas-lovable.md` (structure + inventory
checklist) as a starting point.

## Quality Gate

The Documentation Reviewer issues a PASS/FAIL verdict. If FAIL, the documentation needs fixes.

## Usage

```bash
# Full mode (default): complete documentation
python .hermes/skills/cp-documentation/scripts/run.py "scheduling API for clinics"

# Specific mode: technical documentation only
python .hermes/skills/cp-documentation/scripts/run.py "orders REST API" --mode tech

# Specific mode: user documentation only
python .hermes/skills/cp-documentation/scripts/run.py "delivery mobile app" --mode user

# Specific mode: diagrams only
python .hermes/skills/cp-documentation/scripts/run.py "e-commerce system" --mode diagrams

# Specific mode: API documentation only
python .hermes/skills/cp-documentation/scripts/run.py "authentication endpoints" --mode api

# With input file
python .hermes/skills/cp-documentation/scripts/run.py --input description.txt

# Save output to a specific file
python .hermes/skills/cp-documentation/scripts/run.py "payments API" --output docs/complete.md

# Just view the crew structure
python .hermes/skills/cp-documentation/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-documentation/scripts/run.py \
  "REST API for a medical appointment scheduling system. \
   Endpoints: GET /doctors, POST /appointments, DELETE /appointments/:id. \
   JWT authentication. Email notifications. \
   Technologies: Django REST Framework, PostgreSQL, Redis for the email queue."
```

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.
